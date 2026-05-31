from urllib.parse import parse_qs, urlparse


def to_embed_url(video_url: str) -> str:
    parsed = urlparse(video_url)
    host = parsed.netloc.lower()

    if "youtube.com" in host:
        video_id = parse_qs(parsed.query).get("v", [""])[0]
        if video_id:
            return f"https://www.youtube.com/embed/{video_id}"
    if "youtu.be" in host:
        video_id = parsed.path.strip("/")
        if video_id:
            return f"https://www.youtube.com/embed/{video_id}"
    if "vimeo.com" in host:
        video_id = parsed.path.strip("/").split("/")[-1]
        if video_id:
            return f"https://player.vimeo.com/video/{video_id}"

    return video_url
