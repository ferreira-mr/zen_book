// =============================================================================
// BookForge Core: template-kindle.typ
// Edição Typst para E-Reader Kindle (105x140mm, Proporção 3:4 E-Ink)
// =============================================================================

#import "base-macros.typ": *

#let setup-kindle(doc, book-title: "BookForge Kindle Edition") = {
  set page(
    width: 105mm,
    height: 140mm,
    fill: white,
    margin: (top: 8mm, bottom: 8mm, left: 7mm, right: 7mm),
    footer: context {
      let page-num = counter(page).get().first()
      if page-num > 1 {
        align(right)[
          #text(size: 8pt, font: font-sans, fill: rgb("#444444"))[#page-num]
        ]
      }
    }
  )

  set text(
    font: font-serif,
    size: 9pt,
    fill: black,
    lang: "pt",
    region: "BR"
  )

  set par(
    justify: true,
    leading: 0.60em,
    first-line-indent: 1em,
  )

  doc
}
