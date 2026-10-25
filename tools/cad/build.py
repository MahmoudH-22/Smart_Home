"""Assemble the artifact HTML from template + app.js + scene.json.

Run: python3 build.py out/scene.json page.html
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))

def main(scene_path, out_path, local=False):
    """Inline data and script into the template.

    @param scene_path path to scene.json  @param out_path output html
    @param local wrap in a full document and use local three.js (for testing)
    @returns None
    """
    data = open(scene_path).read().replace("</", "<\\/")
    html = open(os.path.join(HERE, "template.html")).read().replace("__DATA__", data).replace("__APP__", open(os.path.join(HERE, "app.js")).read())
    if local:
        html = html.replace("https://cdn.jsdelivr.net/npm/three@0.147.0/build/three.min.js", "package/build/three.min.js")
        html = html.replace("https://cdn.jsdelivr.net/npm/three@0.147.0/examples/js/controls/OrbitControls.js", "package/examples/js/controls/OrbitControls.js")
        html = '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body>' + html + '</body></html>'
    open(out_path, "w").write(html)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], len(sys.argv) > 3)
