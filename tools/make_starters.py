"""Generate starter.py from each solution.py by removing the marked solution blocks.

    python tools/make_starters.py

In a solution, code between '# >>> SOLUTION' and '# <<< SOLUTION' is replaced by a
NotImplementedError (or left empty when marked '(list)'), and 'STEP n' comments become 'TODO n'.
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]

for solution in sorted(ROOT.glob("exercises/*/solution.py")):
    out, skipping = [], False
    for line in solution.read_text().splitlines():
        if "# >>> SOLUTION" in line:
            skipping = True
            indent = line[: len(line) - len(line.lstrip())]
            if "(list)" in line:                      # inside a list literal: leave it empty
                out.append(f"{indent}# add your entries here")
            else:
                out.append(f'{indent}raise NotImplementedError("Complete the TODO above")')
        elif "# <<< SOLUTION" in line:
            skipping = False
        elif not skipping:
            out.append(re.sub(r"# STEP ([A-D]?\d)", r"# TODO \1", line))
    if not any("NotImplementedError" in l or "add your entries" in l for l in out):
        continue                                      # design-only module: no starter
    text = "\n".join(out) + "\n"
    text = text.replace("solution.py", "starter.py").replace("model answer", "starter")
    (solution.parent / "starter.py").write_text(text)
    print(f"wrote {solution.parent.name}/starter.py ({text.count('TODO ')} TODOs)")
