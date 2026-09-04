from app.services.meme_generator import render_text_target


def test_render_text_target_fits_short_and_long_terms():
    """Test term cards stay inside the compositor's target dimensions."""
    short_term = render_text_target("free threading")
    long_term = render_text_target("asynchronous generator iterator")

    assert short_term.mode == "RGBA"
    assert short_term.width == 220
    assert long_term.width == 220
    assert short_term.height <= 187
    assert long_term.height <= 187
    assert long_term.height > short_term.height
