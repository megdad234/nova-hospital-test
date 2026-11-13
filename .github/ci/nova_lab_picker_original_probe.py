"""Read only the original NOVA lab picker renderer; never print patient data."""
from pathlib import Path
source=Path("hospital/static/app.js").read_text(encoding="utf-8")
for token in ("function testChoices()", "function testChoices(", "class=\"quick-tests\"", "data-pickcheck", "searchTest("):
    start=source.find(token)
    if start>=0:
        print("NOVA_PICKER_SOURCE "+repr(token)+" = "+repr(source[max(0,start-130):start+2600]))
