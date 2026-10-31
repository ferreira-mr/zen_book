// =============================================================================
// BookForge Core: base-macros.typ
// Macros tipográficas e componentes editoriais reutilizáveis em Typst
// =============================================================================

#let font-serif = ("Palatino Linotype", "Book Antiqua", "Georgia", "Libertinus Serif", "serif")
#let font-sans = ("Segoe UI", "Candara", "Optima", "Calibri", "sans-serif")
#let font-mono = ("Consolas", "Cascadia Code", "Courier New", "monospace")

// Cores padrão editoriais
#let cor-bordo = rgb("#7A2424")
#let cor-bordo-escuro = rgb("#5E1919")
#let cor-bordo-claro = rgb("#F5EBEB")
#let cor-azul = rgb("#1D4ED8")
#let cor-azul-claro = rgb("#EFF6FF")
#let cor-texto = rgb("#1C1C1C")
#let cor-creme = rgb("#FBF9F5")
#let cor-cinza = rgb("#666666")
#let cor-cinza-claro = rgb("#F3F4F6")

// Marcador de página original do livro
#let book-page(num, section: "") = [
  #metadata((book_page: num, section: section)) #label("p-" + str(num))
]

// Banner de Abertura de Parte
#let part-banner(num, title, fill-color: cor-bordo) = {
  v(1.5em)
  align(center)[
    #block(
      fill: fill-color,
      inset: (x: 2em, y: 0.8em),
      radius: 3pt,
      width: 100%,
      [
        #text(size: 14pt, font: font-sans, weight: "bold", fill: white, tracking: 0.15em)[
          #upper(num + " – " + title)
        ]
      ]
    )
  ]
  v(1em)
}

// Cabeçalho de Capítulo
#let chapter-header(title, book-page-num: none, stroke-color: cor-bordo) = {
  v(1.2em)
  block(
    width: 100%,
    stroke: (bottom: 1.5pt + stroke-color),
    inset: (bottom: 0.4em),
    grid(
      columns: (1fr, auto),
      align: (left + bottom, right + bottom),
      text(size: 13pt, font: font-sans, weight: "bold", fill: stroke-color, tracking: 0.08em)[
        #upper(title)
      ],
      if book-page-num != none [
        #box(
          fill: stroke-color,
          inset: (x: 8pt, y: 3pt),
          radius: 2pt,
          text(size: 11pt, font: font-sans, weight: "bold", fill: white)[#book-page-num]
        )
      ]
    )
  )
  v(0.8em)
}

// Seção numerada
#let sec(num, title, color: cor-bordo) = {
  v(1em)
  grid(
    columns: (auto, 1fr),
    gutter: 8pt,
    align: (top, top),
    box(
      fill: color,
      inset: (x: 6pt, y: 2pt),
      radius: 2pt,
      text(size: 10pt, font: font-sans, weight: "bold", fill: white)[#num]
    ),
    text(size: 11pt, font: font-sans, weight: "bold", fill: color)[#title]
  )
  v(0.4em)
}

// Caixa de Destaque / Nota
#let feature-box(title: "Observação", body, color: cor-azul) = {
  v(0.6em)
  block(
    fill: color.lighten(92%),
    stroke: (left: 3.5pt + color, rest: 0.5pt + color.lighten(60%)),
    inset: 9pt,
    radius: (right: 3pt),
    width: 100%,
    [
      #if title != "" [
        #text(size: 10pt, font: font-sans, weight: "bold", fill: color)[#title]
        #v(3pt)
      ]
      #text(size: 9.8pt, font: font-serif)[#body]
    ]
  )
  v(0.6em)
}

// Macro para Figuras
#let book-fig(img-path, caption: "", width: 90%) = {
  align(center)[
    #v(4pt)
    #image(img-path, width: width)
    #if caption != "" [
      #v(4pt)
      #text(size: 9pt, font: font-sans, fill: cor-cinza)[#caption]
    ]
    #v(6pt)
  ]
}
