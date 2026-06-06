from app.services.video import to_embed_url, video_tracking_provider


def test_youtube_watch_url_to_embed_url():
    result = to_embed_url("https://www.youtube.com/watch?v=abc123")
    assert result.startswith("https://www.youtube.com/embed/abc123")
    assert "enablejsapi=1" in result


def test_youtu_be_url_to_embed_url():
    result = to_embed_url("https://youtu.be/abc123")
    assert result.startswith("https://www.youtube.com/embed/abc123")
    assert "enablejsapi=1" in result


def test_vimeo_url_to_embed_url():
    assert (
        to_embed_url("https://vimeo.com/12345")
        == "https://player.vimeo.com/video/12345"
    )


def test_video_tracking_provider():
    assert (
        video_tracking_provider("https://www.youtube.com/watch?v=abc123") == "youtube"
    )
    assert video_tracking_provider("https://youtu.be/abc123") == "youtube"
    assert video_tracking_provider("https://vimeo.com/12345") == "vimeo"
    assert video_tracking_provider("https://example.com/embed") == "external"
