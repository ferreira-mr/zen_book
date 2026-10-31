// =============================================================================
// BookForge Core: template-screen.typ
// Edição Typst Conforto em Telas / Estudo (Fundo Creme, Margens Confortáveis)
// =============================================================================

#import "base-macros.typ": *

#let setup-screen(doc, book-title: "BookForge Edition", book-author: "") = {
  set page(
    paper: "a4",
    fill: cor-creme,
    margin: (top: 2.5cm, bottom: 2.5cm, left: 2.5cm, right: 2.5cm),
    header: context {
      let page-num = counter(page).get().first()
      if page-num > 2 {
        grid(
          columns: (1fr, 1fr),
          align: (left, right),
          text(size: 8.5pt, font: font-sans, fill: cor-bordo, weight: "bold", tracking: 0.08em)[
            #upper(book-title)
          ],
          text(size: 8.5pt, font: font-sans, fill: cor-cinza)[
            #book-author
          ]
        )
        line(length: 100%, stroke: 0.5pt + cor-cinza.lighten(50%))
      }
    },
    footer: context {
      let page-num = counter(page).get().first()
      if page-num > 1 {
        line(length: 100%, stroke: 0.5pt + rgb("#D0D0D0"))
        v(2pt)
        grid(
          columns: (1fr, auto),
          align: (left, right),
          text(size: 8.5pt, font: font-sans, fill: cor-cinza)[
            Edição Editorial de Alta Qualidade
          ],
          text(size: 9.5pt, font: font-serif, weight: "bold", fill: cor-texto)[
            #page-num
          ]
        )
      }
    }
  )

  set text(
    font: font-serif,
    size: 10.5pt,
    fill: cor-texto,
    lang: "pt",
    region: "BR"
  )

  set par(
    justify: true,
    leading: 0.72em,
    first-line-indent: 1.5em,
  )

  doc
}
