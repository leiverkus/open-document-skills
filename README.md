# Open Document Skills

Codex skills for OpenDocument Format files:

- `odt` - OpenDocument Text / LibreOffice Writer
- `odp` - OpenDocument Presentation / LibreOffice Impress
- `ods` - OpenDocument Spreadsheet / LibreOffice Calc
- `odg` - OpenDocument Graphics / LibreOffice Draw

The skills favor native ODF package/XML workflows over unnecessary Office-format round trips. Each skill includes small Python helper scripts for direct generation, package inspection, XML-safe edits, validation, and rendering/export workflows where LibreOffice is available.

## Layout

```text
skills/
  odt/
  odp/
  ods/
  odg/
tests/
  fixtures/
  test_*.py
```

## Testing

Run the smoke tests:

```bash
python -m unittest discover -s tests
```

The test module is also compatible with `pytest` if you prefer it. LibreOffice-dependent rendering/recalc behavior is treated as optional in tests and should be checked manually when `soffice` is available.

## License

MIT. See [LICENSE](LICENSE).
