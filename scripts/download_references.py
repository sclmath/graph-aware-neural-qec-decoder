#!/usr/bin/env python3
"""Download the papers listed in docs/references/references.md, preferring arXiv preprints."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import sys
import time
import unicodedata
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin, urlparse
from xml.etree import ElementTree as ET

import requests

warnings.filterwarnings("ignore", message=".*RequestsDependencyWarning.*")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36 "
    "CodexReferenceDownloader/1.0"
)
S2_BATCH = "https://api.semanticscholar.org/graph/v1/paper/batch"
OPENALEX_WORK = "https://api.openalex.org/works/"
ARXIV_API = "https://export.arxiv.org/api/query"
CROSSREF_WORK = "https://api.crossref.org/works/"
ARXIV_NS = {"a": "http://www.w3.org/2005/Atom"}
ARXIV_OVERRIDES = {"R43": "2406.14527"}


def log(message: str) -> None:
    print(message, flush=True)


def normalize_title(value: str) -> str:
    value = html.unescape(value).lower()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def extract_arxiv(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    bare = re.fullmatch(r"(\d{4}\.\d{4,5}|[a-z0-9.\-]+/\d{7})(?:v\d+)?", value, flags=re.IGNORECASE)
    if bare:
        return re.sub(r"v\d+$", "", bare.group(1), flags=re.IGNORECASE)
    patterns = [
        r"(?:arxiv\.org/(?:abs|pdf)/|10\.48550/arxiv\.)([a-z0-9.\-]+/\d{7}|\d{4}\.\d{4,5})(?:v\d+)?",
        r"arxiv[:\s/]+([a-z0-9.\-]+/\d{7}|\d{4}\.\d{4,5})(?:v\d+)?",
    ]
    for pattern in patterns:
        match = re.search(pattern, value, flags=re.IGNORECASE)
        if match:
            ident = match.group(1).strip().rstrip(".")
            return re.sub(r"v\d+$", "", ident, flags=re.IGNORECASE)
    return None


def extract_doi(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"10\.\d{4,9}/[^\s\]\[()<>]+", value, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(0).rstrip(".,;").rstrip(")")


def parse_references(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(
        r"^- \*\*\[(R\d+)\]\s*(.*?)\*\*\s*(.*?)\s*\[([^\]]+)\]\((https?://[^)]+)\)\s*$",
        flags=re.MULTILINE,
    )
    refs: list[dict[str, Any]] = []
    for match in pattern.finditer(text):
        ref_id, bold, tail, label, url = match.groups()
        year_match = re.search(r"\((\d{4})\)\.\s*(.+?)(?:\.)?$", bold)
        if year_match:
            year = int(year_match.group(1))
            title = year_match.group(2).strip()
        else:
            year = None
            title = bold.strip()
        doi = extract_doi(url) or extract_doi(label)
        arxiv_id = extract_arxiv(url) or extract_arxiv(label)
        refs.append(
            {
                "id": ref_id,
                "title": title,
                "year": year,
                "doi": doi,
                "url": url,
                "label": label,
                "arxiv_id": arxiv_id,
                "tail": tail,
            }
        )
    if not refs:
        raise RuntimeError(f"No references parsed from {path}")
    for ref in refs:
        ref["arxiv_id"] = ref.get("arxiv_id") or ARXIV_OVERRIDES.get(ref["id"])
    return refs


def semantic_scholar_metadata(refs: list[dict[str, Any]]) -> list[dict[str, Any] | None]:
    ids: list[str] = []
    for ref in refs:
        if ref.get("doi"):
            ids.append(f"DOI:{ref['doi']}")
        elif ref.get("arxiv_id"):
            ids.append(f"ARXIV:{ref['arxiv_id']}")
        else:
            ids.append("")
    results: list[dict[str, Any] | None] = [None] * len(ids)
    nonempty = [(i, value) for i, value in enumerate(ids) if value]
    params = {"fields": "title,externalIds,openAccessPdf,url"}
    for start in range(0, len(nonempty), 50):
        chunk = nonempty[start : start + 50]
        payload = {"ids": [value for _, value in chunk]}
        for attempt in range(2):
            try:
                response = requests.post(
                    S2_BATCH,
                    params=params,
                    json=payload,
                    headers={"User-Agent": USER_AGENT},
                    timeout=60,
                )
                if response.status_code == 429:
                    wait = 5 * (attempt + 1)
                    log(f"Semantic Scholar rate limit; waiting {wait}s")
                    time.sleep(wait)
                    continue
                response.raise_for_status()
                decoded = response.json()
                for (index, _), item in zip(chunk, decoded):
                    results[index] = item
                break
            except Exception as exc:
                if attempt == 1:
                    log(f"Semantic Scholar metadata warning: {exc}")
                else:
                    time.sleep(2)
        if start + 50 < len(nonempty):
            time.sleep(1)
    return results


def arxiv_search(title: str) -> str | None:
    query = f'ti:"{title}"'
    try:
        response = requests.get(
            ARXIV_API,
            params={"search_query": query, "start": 0, "max_results": 5},
            headers={"User-Agent": USER_AGENT},
            timeout=30,
        )
        response.raise_for_status()
        root = ET.fromstring(response.content)
    except Exception:
        return None
    target = normalize_title(title)
    best: tuple[int, str] | None = None
    for entry in root.findall("a:entry", ARXIV_NS):
        title_node = entry.find("a:title", ARXIV_NS)
        id_node = entry.find("a:id", ARXIV_NS)
        if title_node is None or id_node is None:
            continue
        candidate_title = normalize_title(" ".join(title_node.text.split()))
        candidate_id = extract_arxiv(id_node.text)
        if not candidate_id:
            continue
        if candidate_title == target:
            return candidate_id
        if candidate_title.startswith(target) or target.startswith(candidate_title[: max(20, len(target) - 12)]):
            score = abs(len(candidate_title) - len(target))
            if best is None or score < best[0]:
                best = (score, candidate_id)
    return best[1] if best else None


def openalex_metadata(ref: dict[str, Any]) -> dict[str, Any] | None:
    try:
        if ref.get("doi"):
            url = OPENALEX_WORK + "https://doi.org/" + ref["doi"]
            response = requests.get(
                url,
                params={"mailto": "codex.reference.downloader@example.com"},
                headers={"User-Agent": USER_AGENT},
                timeout=30,
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        response = requests.get(
            OPENALEX_WORK,
            params={"search": ref["title"], "per-page": 3, "mailto": "codex.reference.downloader@example.com"},
            headers={"User-Agent": USER_AGENT},
            timeout=30,
        )
        response.raise_for_status()
        results = response.json().get("results", [])
        target = normalize_title(ref["title"])
        for item in results:
            if normalize_title(item.get("title") or "") == target:
                return item
        return results[0] if results else None
    except Exception:
        return None


def crossref_metadata(doi: str | None) -> dict[str, Any] | None:
    if not doi:
        return None
    try:
        response = requests.get(
            CROSSREF_WORK + quote(doi, safe=""),
            headers={"User-Agent": USER_AGENT},
            timeout=30,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json().get("message")
    except Exception:
        return None


def unique_urls(values: list[str | None]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not value:
            continue
        value = html.unescape(value.strip())
        if value.startswith("//"):
            value = "https:" + value
        if not value.startswith(("http://", "https://")):
            continue
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def collect_candidates(
    ref: dict[str, Any], s2: dict[str, Any] | None, openalex: dict[str, Any] | None, crossref: dict[str, Any] | None
) -> tuple[list[str], list[str]]:
    arxiv_ids: list[str] = []
    metadata_urls: list[str] = []
    for value in [
        ref.get("arxiv_id"),
        ((s2 or {}).get("externalIds") or {}).get("ArXiv"),
        ((openalex or {}).get("ids") or {}).get("arxiv"),
    ]:
        ident = extract_arxiv(value)
        if ident and ident not in arxiv_ids:
            arxiv_ids.append(ident)

    s2_oa = (s2 or {}).get("openAccessPdf") or {}
    openalex = openalex or {}
    open_access = openalex.get("open_access") or {}
    best_oa_location = openalex.get("best_oa_location") or {}
    metadata_urls.append(s2_oa.get("url"))
    metadata_urls.append(open_access.get("oa_url"))
    metadata_urls.append(best_oa_location.get("pdf_url"))

    for location in openalex.get("locations", []) or []:
        metadata_urls.append(location.get("pdf_url"))
        landing = location.get("landing_page_url")
        if landing and "arxiv.org/abs/" in landing:
            metadata_urls.append(landing.replace("/abs/", "/pdf/"))
        elif landing and location.get("is_oa"):
            metadata_urls.append(landing)

    for link in (crossref or {}).get("link", []) or []:
        content_type = (link.get("content-type") or "").lower()
        url = link.get("URL")
        if "pdf" in content_type or (url and ".pdf" in url.lower()):
            metadata_urls.append(url)
        elif url:
            metadata_urls.append(url)

    primary = (crossref or {}).get("URL") or ref.get("url")
    metadata_urls.append(primary)
    if ref.get("doi"):
        metadata_urls.append("https://doi.org/" + ref["doi"])

    arxiv_urls: list[str] = []
    for ident in arxiv_ids:
        arxiv_urls.extend([f"https://arxiv.org/pdf/{ident}", f"https://export.arxiv.org/pdf/{ident}"])
    return unique_urls(arxiv_urls), unique_urls(metadata_urls)


def scrape_pdf_links(page_url: str) -> list[str]:
    try:
        response = requests.get(
            page_url,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
            timeout=30,
            allow_redirects=True,
        )
        content_type = response.headers.get("content-type", "").lower()
        if response.status_code >= 400 or "html" not in content_type or len(response.content) > 5_000_000:
            return []
        text = response.text
    except Exception:
        return []
    urls: list[str] = []
    meta_patterns = [
        r'<meta[^>]+name=["\']citation_pdf_url["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']citation_pdf_url["\']',
        r'<meta[^>]+property=["\']og:pdf["\'][^>]+content=["\']([^"\']+)',
    ]
    for pattern in meta_patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            urls.append(urljoin(response.url, html.unescape(match.group(1))))
    for match in re.finditer(r'href=["\']([^"\']+(?:\.pdf|/pdf/?)(?:\?[^"\']*)?)["\']', text, flags=re.IGNORECASE):
        urls.append(urljoin(response.url, html.unescape(match.group(1))))
    return unique_urls(urls)[:20]


def download_pdf(url: str, destination: Path, session: requests.Session) -> tuple[bool, dict[str, Any]]:
    info: dict[str, Any] = {"url": url}
    part = destination.with_suffix(destination.suffix + ".part")
    try:
        response = session.get(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/pdf,application/octet-stream,*/*;q=0.8",
                "Referer": "https://scholar.google.com/",
            },
            stream=True,
            allow_redirects=True,
            timeout=(20, 90),
        )
        info["status_code"] = response.status_code
        info["content_type"] = response.headers.get("content-type", "")
        info["final_url"] = response.url
        response.raise_for_status()
        content_length = int(response.headers.get("content-length") or 0)
        if content_length > 250_000_000:
            raise ValueError(f"file too large ({content_length} bytes)")
        first = b""
        size = 0
        digest = hashlib.sha256()
        with part.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if not chunk:
                    continue
                if not first:
                    first = chunk[:1024]
                if size == 0 and not first.lstrip().startswith(b"%PDF"):
                    raise ValueError("response is not a PDF")
                size += len(chunk)
                digest.update(chunk)
                handle.write(chunk)
        if size < 20_000:
            raise ValueError(f"PDF is unexpectedly small ({size} bytes)")
        part.replace(destination)
        info.update({"size": size, "sha256": digest.hexdigest(), "ok": True})
        return True, info
    except Exception as exc:
        try:
            part.unlink(missing_ok=True)
        except Exception:
            pass
        info["error"] = str(exc)
        info["ok"] = False
        return False, info


def safe_filename(ref: dict[str, Any]) -> str:
    title = ref["title"].replace("–", "-").replace("—", "-")
    title = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", "", title)
    title = re.sub(r"\s+", "_", title).strip("._")
    return f"{ref['id']}_{title[:110]}.pdf"


def write_manifest(output_dir: Path, records: list[dict[str, Any]]) -> None:
    manifest = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "total": len(records),
        "downloaded": sum(1 for row in records if row["status"] == "downloaded"),
        "failed": sum(1 for row in records if row["status"] != "downloaded"),
        "records": records,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    with (output_dir / "manifest.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["id", "status", "title", "doi", "arxiv_id", "file", "source_url", "size", "sha256", "error"],
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(records)

    lines = [
        "# 文献 PDF 下载清单",
        "",
        f"- 生成时间：{manifest['generated_at']}",
        f"- 总计：{manifest['total']}",
        f"- 已下载：{manifest['downloaded']}",
        f"- 未下载：{manifest['failed']}",
        "",
        "| 编号 | 状态 | 文献 | 来源 | 文件 |",
        "|---|---|---|---|---|",
    ]
    for row in records:
        status = "已下载" if row["status"] == "downloaded" else "未下载"
        source = row.get("source_url") or ""
        file_name = row.get("file") or ""
        title = str(row["title"]).replace("|", "\\|")
        lines.append(f"| {row['id']} | {status} | {title} | {source} | {file_name} |")
    (output_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--references", default="docs/references/references.md")
    parser.add_argument("--output", default="docs/references/references_pdfs")
    parser.add_argument("--only", nargs="*", help="Optional reference IDs, e.g. R01 R02")
    parser.add_argument("--retry-failed", action="store_true", help="Retry entries without an existing valid PDF")
    args = parser.parse_args()

    references_path = Path(args.references).resolve()
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    refs = parse_references(references_path)
    if args.only:
        wanted = {item.upper() for item in args.only}
        refs = [ref for ref in refs if ref["id"] in wanted]

    log(f"Parsed {len(refs)} references")
    log("Resolving Semantic Scholar metadata in batches")
    s2_items = semantic_scholar_metadata(refs)

    log("Resolving OpenAlex metadata")
    openalex_items: list[dict[str, Any] | None] = [None] * len(refs)
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(openalex_metadata, ref): index for index, ref in enumerate(refs)}
        for future in as_completed(futures):
            index = futures[future]
            try:
                openalex_items[index] = future.result()
            except Exception:
                openalex_items[index] = None

    previous_records: dict[str, dict[str, Any]] = {}
    previous_manifest = output_dir / "manifest.json"
    if previous_manifest.exists():
        try:
            for row in json.loads(previous_manifest.read_text(encoding="utf-8")).get("records", []):
                previous_records[row.get("id")] = row
        except Exception:
            pass

    records: list[dict[str, Any]] = []
    session = requests.Session()
    for index, ref in enumerate(refs):
        s2 = s2_items[index]
        openalex = openalex_items[index]
        crossref = crossref_metadata(ref.get("doi"))
        arxiv_urls, metadata_urls = collect_candidates(ref, s2, openalex, crossref)
        destination = output_dir / safe_filename(ref)
        existing = destination.exists() and destination.stat().st_size >= 20_000
        if existing and not args.retry_failed:
            with destination.open("rb") as handle:
                digest = hashlib.sha256()
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            prior = previous_records.get(ref["id"], {})
            record = {
                **ref,
                "status": "downloaded",
                "file": destination.name,
                "source_url": prior.get("source_url") or "existing-file",
                "size": destination.stat().st_size,
                "sha256": digest.hexdigest(),
                "error": "",
                "kind": prior.get("kind", ""),
                "candidate_sources": arxiv_urls + metadata_urls,
            }
            records.append(record)
            write_manifest(output_dir, records)
            log(f"[{ref['id']}] existing: {destination.name}")
            continue

        candidates = arxiv_urls + metadata_urls
        attempts: list[dict[str, Any]] = []
        success: dict[str, Any] | None = None
        kind = "direct"
        for candidate in candidates:
            ok, info = download_pdf(candidate, destination, session)
            info["candidate"] = candidate
            attempts.append(info)
            if ok:
                success = info
                kind = "arxiv" if candidate in arxiv_urls else "open-access"
                break
            # If a landing page has an embedded PDF link, try it immediately.
            if "html" in str(info.get("content_type", "")).lower():
                for embedded in scrape_pdf_links(candidate):
                    ok, embedded_info = download_pdf(embedded, destination, session)
                    embedded_info["candidate"] = embedded
                    embedded_info["discovered_from"] = candidate
                    attempts.append(embedded_info)
                    if ok:
                        success = embedded_info
                        kind = "embedded-pdf"
                        break
                if success:
                    break

        # Last resort for works that metadata providers did not connect to an arXiv version.
        if not success and not arxiv_urls:
            time.sleep(0.2)
            searched_id = arxiv_search(ref["title"])
            if searched_id:
                log(f"[{ref['id']}] arXiv title match: {searched_id}")
                for candidate in [
                    f"https://arxiv.org/pdf/{searched_id}",
                    f"https://export.arxiv.org/pdf/{searched_id}",
                ]:
                    ok, info = download_pdf(candidate, destination, session)
                    info["candidate"] = candidate
                    info["discovered_by"] = "arxiv-title-search"
                    attempts.append(info)
                    if ok:
                        success = info
                        kind = "arxiv-title-search"
                        ref["arxiv_id"] = searched_id
                        break

        if success:
            record = {
                **ref,
                "status": "downloaded",
                "file": destination.name,
                "source_url": success["final_url"],
                "size": success["size"],
                "sha256": success["sha256"],
                "error": "",
                "kind": kind,
                "candidate_sources": candidates,
                "attempts": attempts,
            }
            log(f"[{ref['id']}] downloaded {destination.name} ({success['size']//1024} KiB) from {kind}")
        else:
            last_error = attempts[-1].get("error", "no downloadable candidate") if attempts else "no candidate"
            record = {
                **ref,
                "status": "failed",
                "file": "",
                "source_url": "",
                "size": 0,
                "sha256": "",
                "error": last_error,
                "kind": "",
                "candidate_sources": candidates,
                "attempts": attempts,
            }
            log(f"[{ref['id']}] FAILED: {last_error}")
        records.append(record)
        write_manifest(output_dir, records)

    write_manifest(output_dir, records)
    final_manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    log(f"Finished: {final_manifest['downloaded']}/{final_manifest['total']} downloaded")
    return 0 if final_manifest["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
