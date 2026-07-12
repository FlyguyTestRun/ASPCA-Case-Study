# Assessment

`ASSESSMENT.md` is the source; `ASSESSMENT.docx` is generated from it for a
polished, submittable Word copy. Rebuild after any edit to the markdown:

```bash
cd assessment
npm install docx    # only needed once
node build_docx.js
```

`build_docx.js` mirrors the markdown's structure by hand (headings, bold
leads, bullets) rather than a generic markdown-to-docx converter, so the
Word output gets deliberate typography (US Letter, a consistent accent
color, real bullet lists) instead of default styling.
