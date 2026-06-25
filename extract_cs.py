import argparse
from pathlib import Path
import os
import re
import posixpath
import re
from urllib.parse import urlsplit, unquote, urlparse, parse_qs


FLAVOR_DEF = {
    b"NF30PS00": { # P900i, p903itv
        "meta_start": 0xC,
        "url_size_off": 0x4,
        "response_off": 0x8,
        "file_off": 0xC,
        "content_off": 0x20,
    },
    b"NF32PS00": { # N902i, N903i, N905i
        "meta_start": 0xC,
        "url_size_off": 0x4,
        "response_off": 0xC,
        "file_off": 0x10,
        "content_off": 0x34,
    },
    
}

EXTS = (".htm", ".html", ".gif", ".jpeg", ".jpg", ".png", ".bmp", ".swf", ".mld")

def flatten_img_src(html, encoding):
    IMAGE_EXTS = (".gif", ".jpeg", ".jpg", ".png", ".bmp")
    exts_str = "|".join([f"\\{ext}" for ext in IMAGE_EXTS])
    EXTS_RE = re.compile(rf"([^/\\?#]+(?:{exts_str}))", flags=re.IGNORECASE)

    def repl(m):
        prefix = m.group("prefix")
        quote = m.group("quote")
        src = m.group("srcq") if m.group("srcq") is not None else m.group("srcu")

        parts = urlsplit(src)
        qs = parse_qs(parts.query, encoding=encoding)
        
        filename = os.path.basename(unquote(parts.path, encoding=encoding))
        
        if not filename or not filename.endswith(IMAGE_EXTS):
            for v in [v for vs in qs.values() for v in vs]:
                if (m2 := EXTS_RE.search(v)) is not None:
                    filename = m2[1]
                    break

        if not filename:
            return m.group(0)

        new_src = f"./{filename}"
        if quote:
            return f'{prefix}{quote}{new_src}{quote}'
        return f"{prefix}{new_src}"

    return re.sub(
        r'(?P<prefix><img\b[^>]*?\bsrc\s*=\s*)(?:(?P<quote>["\'])(?P<srcq>.*?)(?P=quote)|(?P<srcu>[^>\s]+))(?=[\s>/])',
        repl,
        html,
        flags=re.IGNORECASE | re.DOTALL
    )


def get_ext(response):
    if not (m := re.search(r"Content-Type:\s*(.+)", response, re.IGNORECASE)):
        return "bin"
    
    content_type = m.group(1).lower()

    mime_to_ext = {
        "text/html": "html",
        "application/xhtml+xml": "html",
        "image/gif": "gif",
        "image/jpeg": "jpeg",
        "image/png": "png",
        "image/bmp": "bmp",
        "image/x-ms-bmp": "bmp",
        "application/x-shockwave-flash": "swf",
        "audio/midi": "mid",
        "audio/mid": "mid",
    }

    for mime, ext in mime_to_ext.items():
        if mime in content_type:
            return ext
            
    return "bin"


def get_html_title(html):
    m = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)

    if m is None or m[1].isspace():
        return None
    else:
        return m[1].strip()


TRANSLATION_TABLE = str.maketrans({
    "\\": "＼",
    "/": "／",
    ":": "：",
    "*": "＊",
    "?": "？",
    '"': "”",
    "<": "＜",
    ">": "＞",
    "|": "｜",
})

def sanitize_filename(filename: str) -> str:
    sanitized = filename.translate(TRANSLATION_TABLE)

    sanitized = "".join(
        " " if ord(c) < 32 else c
        for c in sanitized
    )

    if not sanitized:
        sanitized = "untitled"

    return sanitized


def get_charset_from_html(html_bytes):
    m = re.search(
        br'charset\s*=\s*["\']?\s*([^"\'\s;>]+)',
        html_bytes[:4096],
        re.IGNORECASE
    )
    if m:
        return m.group(1).decode("ascii", "ignore").lower()
    return None


def get_charset_from_header(header_bytes):
    m = re.search(
        br"Content-Type:[^\r\n]*charset\s*=\s*([^\s;\r\n]+)",
        header_bytes,
        re.I,
    )
    return m.group(1).decode("ascii", "ignore") if m else None


def get_parameter_filename(url, encoding):
    parsed_url = urlparse(url)
    params = parse_qs(parsed_url.query, encoding=encoding)

    exts_str = "|".join([f"\\{ext}" for ext in EXTS])
    EXTS_RE = re.compile(rf"([^/\\?#]+(?:{exts_str}))", flags=re.IGNORECASE)

    for vs in params.values():
        for v in vs:
            if (m := EXTS_RE.search(v)) is not None:
                return m[1]
    
    return None


def convert(input_path, out_dir, change_image_url, verbose):
    with open(input_path, "rb") as inf:
        cs = inf.read()

    magic = cs[:8]
    if magic not in FLAVOR_DEF.keys():
        raise ValueError(f"wrong magic {magic}")

    os.makedirs(out_dir, exist_ok=True)

    meta_start = FLAVOR_DEF[magic]["meta_start"]
    url_size_off = FLAVOR_DEF[magic]["url_size_off"]
    response_off = FLAVOR_DEF[magic]["response_off"]
    file_off = FLAVOR_DEF[magic]["file_off"]
    content_off = FLAVOR_DEF[magic]["content_off"]

    off = meta_start
    cs_size = len(cs)
    encoding = "cp932"
    while off < cs_size:
        url_size = int.from_bytes(cs[off + url_size_off : off + url_size_off + 0x4], "little")
        response_size = int.from_bytes(cs[off + response_off : off + response_off + 0x4], "little")
        file_size = int.from_bytes(cs[off + file_off : off + file_off + 0x4], "little")
        content_start= off + content_off
        if verbose:
            print(f"{hex(off)}, url_size: {hex(url_size)}, response_size: {hex(response_size)}, file_size: {hex(file_size)}, content_start: {hex(content_start)}")

        if sum([url_size, response_size, file_size]) == 0:
            break
        
        url = cs[content_start : content_start + url_size].decode("ascii")

        response_start = content_start + url_size
        response_data = cs[response_start : response_start + response_size]
        response_text = response_data.decode("cp932")

        file_start = response_start + response_size
        file_data = cs[file_start : file_start + file_size]

        filename = unquote(urlparse(url).path, encoding=encoding)
        filename = posixpath.basename(filename)

        if not filename.lower().endswith(EXTS):
            if (tmp := get_parameter_filename(url, encoding)) is not None:
                filename = tmp
        
        if not filename or filename.isspace():
            filename = "index"

        basename = os.path.splitext(filename)[0]

        if not filename.lower().endswith(EXTS):
            filename = basename + "." + get_ext(response_text)

        with open(out_dir / f"{filename}.txt", "wb") as outf:
            outf.write(f"[URL]\n{url}\n\n[Response Header]\n".encode("ascii") + response_data)

        if filename.endswith((".html", ".htm")) and change_image_url:
            try:
                encoding = get_charset_from_header(response_data) or get_charset_from_html(file_data) or encoding
                encoding = "cp932" if encoding.lower() in ["shift-jis", "shiftjis", "shift_jis", "x-sjis"] else encoding
                html = file_data.decode(encoding)
                html = flatten_img_src(html, encoding=encoding)
                title = get_html_title(html)
                print(f"Title: {title}")
                print(f"Encoding: {encoding}")
                file_data = html.encode(encoding)
            except Exception as e:
                print(f"HTML Conversion Failed: {e}")

        with open(out_dir / f"{filename}", "wb") as outf:
            outf.write(file_data)
        
        print(Path(url), "=>", filename)
        if verbose:
            print()

        off = file_start + file_size
    
    print(f"\noutput => {out_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=""
    )
    parser.add_argument("input", help="Input CS file or directory to extract.")
    parser.add_argument("-o", "--out_dir", default=None, help="Output directory for extracted files.")
    parser.add_argument("-c", "--change-image-url", action="store_true", help="Change image URLs to local relative paths in extracted HTML files.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print verbose processing information.")
    args = parser.parse_args()

    input_ = Path(args.input)

    if input_.is_dir():
        for p in input_.iterdir():
            if p.is_file():
                if args.out_dir is None:
                    out_dir = p.with_name(p.stem + "_extracted")
                else:
                    out_dir = Path(args.out_dir)

                try:   
                    print(f"\n[{p.name}]")
                    convert(p, out_dir, args.change_image_url, args.verbose)
                except Exception as e:
                    print("Error:", e)
    else:
        if args.out_dir is None:
            out_dir = input_.with_name(input_.stem + "_extracted")
        else:
            out_dir = Path(args.out_dir)
        convert(input_, out_dir, args.change_image_url, args.verbose)
