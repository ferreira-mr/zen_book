#import "../template.typ": *

#book-page(1, section: "Introdução")

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
