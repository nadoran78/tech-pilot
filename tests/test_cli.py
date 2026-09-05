"""Tests for the bootstrap command-line interface."""

from tech_pilot.cli import build_parser, main


def test_parser_describes_bootstrap_cli() -> None:
    parser = build_parser()

    assert parser.prog == "tech-pilot"
    assert "AI technology news collection" in parser.format_help()


def test_main_accepts_no_arguments() -> None:
    assert main([]) == 0
