// =============================================================================
// BookForge Core: template-print.typ
// Edição Typst Impressão A4 (Fundo Branco Puro, Contraste de Tinta)
// =============================================================================

#import "base-macros.typ": *

#let setup-print(doc, book-title: "BookForge Edition", book-author: "") = {
  set page(
    paper: "a4",
    fill: white,
    margin: (top: 2.5cm, bottom: 2.5cm, left: 2.8cm, right: 2.2cm),
    header: context {
      let page-num = counter(page).get().first()
      if page-num > 2 {
        grid(
          columns: (1fr, 1fr),
          align: (left, right),
          text(size: 8.5pt, font: font-sans, fill: rgb("#000000"), weight: "bold", tracking: 0.08em)[
            #upper(book-title)
          ],
          text(size: 8.5pt, font: font-sans, fill: rgb("#444444"))[
            #book-author
          ]
        )
        line(length: 100%, stroke: 0.5pt + rgb("#CCCCCC"))
      }
    },
    footer: context {
      let page-num = counter(page).get().first()
      if page-num > 1 {
        line(length: 100%, stroke: 0.5pt + rgb("#CCCCCC"))
        v(2pt)
        grid(
          columns: (1fr, auto),
          align: (left, right),
          text(size: 8pt, font: font-sans, fill: rgb("#666666"))[
            Edição para Impressão
          ],
          text(size: 9.5pt, font: font-serif, weight: "bold", fill: black)[
            #page-num
          ]
        )
      }
    }
  )

  set text(
    font: font-serif,
    size: 10pt,
    fill: black,
    lang: "pt",
    region: "BR"
  )

  set par(
    justify: true,
    leading: 0.68em,
    first-line-indent: 1.5em,
  )

  doc
}
