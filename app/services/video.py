from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


def _with_query(url: str, **params: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    for key, value in params.items():
        query[key] = [value]
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


def to_embed_url(video_url: str) -> str:
    parsed = urlparse(video_url)
    host = parsed.netloc.lower()

    if "youtube.com" in host:
        video_id = parse_qs(parsed.query).get("v", [""])[0]
        if video_id:
            return _with_query(
                f"https://www.youtube.com/embed/{video_id}",
                enablejsapi="1",
                rel="0",
                modestbranding="1",
            )
    if "youtu.be" in host:
        video_id = parsed.path.strip("/")
        if video_id:
            return _with_query(
                f"https://www.youtube.com/embed/{video_id}",
                enablejsapi="1",
                rel="0",
                modestbranding="1",
            )
    if "vimeo.com" in host:
        video_id = parsed.path.strip("/").split("/")[-1]
        if video_id:
            return f"https://player.vimeo.com/video/{video_id}"

    return video_url


def video_tracking_provider(video_url: str) -> str:
    host = urlparse(video_url).netloc.lower()
    if "youtube.com" in host or "youtu.be" in host:
        return "youtube"
    if "vimeo.com" in host:
        return "vimeo"
    return "external"
