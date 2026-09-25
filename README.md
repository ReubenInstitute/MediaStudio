# ScripturesStudio

Flask app for editing Reuben Institute's Psalms and Parashot text, audio
timing, and covers, and exporting the Psalms and Parashot video series
from them.

Runs both from a full recursive git clone (submodules under `audio/`,
`assets`, `fonts`) and from the installed `scripturesstudio` deb, which
pulls its data from the separate `audiobible-*`, `scripturesstudio-assets`,
and `fonts` packages instead.

The dev server (`ScripturesStudio.py` run directly from a clone) uses
`tls.py` for a self-signed HTTPS debug listener. The installed
`scripturesstudio` deb drops `tls.py` and runs under gunicorn instead;
put nginx in front for HTTPS. Sample systemd/nginx configs are installed
under `/usr/share/doc/scripturesstudio/examples/`.

## License

- `scripturesstudio` — code, GPL-3.
