#import "template.typ": *

#set page(
  paper: "a4",
  fill: cor-creme,
  margin: (top: 2.5cm, bottom: 2.5cm, left: 2.5cm, right: 2.5cm),
  header: none,
  footer: context {
    let p = counter(page).get().first()
    if p > 1 {
      align(right)[#text(size: 8.5pt, font: font-sans, fill: cor-cinza)[#p]]
    }
  }
)
#set text(font: font-serif, size: 11pt, fill: cor-texto, lang: "pt")
#set par(justify: true, leading: 0.7em)

#part-banner("I", "DEMONSTRAÇÃO EDITORIAL BOOKFORGE")

#sec("1", "PROJETO GRÁFICO E TIPOGRAFIA DE ALTA DEFINIÇÃO")

Este livro serve como modelo padrão e projeto de teste para a plataforma *BookForge*. Ele demonstra a renderização vetorial de componentes editoriais modernos, caixas de destaque pedagógicas e suporte a equações matemáticas sem depender de imagens rasterizadas de baixa resolução.

#feature-box(title: "Observação Pedagógica")[
  As caixas de destaque são diagramadas com bordas de alto contraste e tipografia clara, garantindo legibilidade tanto em telas coloridas quanto em leitores de tinta eletrônica (E-Ink como Amazon Kindle).
]

#sec("2", "FÓRMULAS MATEMÁTICAS VETORIAIS")

Fórmulas matemáticas são compiladas diretamente no motor tipográfico vetorial:

$ E = m c^2 $

$ frac(-b plus.minus sqrt(b^2 - 4 a c), 2 a) $

#sec("3", "TABELAS E COMPARAÇÕES")

#align(center)[
  #table(
    columns: (auto, 1fr, 1fr),
    align: (center, left, left),
    stroke: 0.5pt + cor-cinza.lighten(50%),
    table.header([*Formato*], [*Resolução*], [*Dispositivo Alvo*]),
    [Screen PDF], [185x260mm Vetorial], [Computadores, Tablets e iPads],
    [Print A4], [210x297mm 300+ DPI], [Gráficas e Impressão Física],
    [Kindle PDF], [105x140mm Fluido], [Amazon Kindle Paperwhite e Oasis],
    [Kindle EPUB], [Refluxável XHTML5], [Amazon Kindle e Leitores Móveis],
  )
]
