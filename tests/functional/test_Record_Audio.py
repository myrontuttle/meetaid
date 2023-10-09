"""Record Audio feature tests."""

from pytest_bdd import given, scenario, then, when


@scenario("../features/Record_Audio.feature", "Record Audio")
def test_record_audio():
    """Record Audio."""


@given("a meeting")
def meeting():
    """a meeting."""


@when("I select record")
def select_record():
    """I select record."""


@then("the audio from my computer is recorded")
def audio_recorded():
    """the audio from my computer is recorded."""
