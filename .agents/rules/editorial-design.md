# Regras de Design Editorial do BookForge (Tela, Impressão A4 & Kindle)

Este documento estabelece as diretrizes visuais e tipográficas para a produção de livros no ecossistema BookForge.

---

## 1. Política de Cabeçalhos e Rodapés (`CLEAN_PAGE_CHROME`)

Para garantir máxima imersão e eliminar distrações durante a leitura:

1. **Cabeçalho (Header):**
   - Deve ser **100% limpo** em todas as edições em PDF.
   - Proibido exibir títulos de capítulos, URLs promocionais, data ou linhas horizontais decorativas.
2. **Rodapé (Footer):**
   - O rodapé deve conter **exclusivamente o número da página atual no canto inferior direito**.
   - O centro e a esquerda do rodapé devem permanecer vazios.
3. **Formato Kindle EPUB:**
   - A paginação e informações de tempo restante são delegadas nativamente ao motor de renderização do e-reader.

---

## 2. Proibição de Rótulos Genéricos Artificiais

- **NUNCA** adicione prefixos como `"Nota:"`, `"Dica:"`, `"Aviso:"` ou emojis antes de títulos de seções ou quadros que já possuem título próprio no livro original.
- Mantenha estritamente o título original traduzido (ex.: `Objetivos de Aprendizagem`, `Outro Ponto de Vista`, `Análise Retórica`).

---

## 3. Diretrizes de Cores e Contraste

### Edição para Leitura em Telas (`-screen.pdf`):
- Fundo: Neutro claro ou creme suave (`#FAF8F5`).
- Texto: Grafite escuro de alta legibilidade (`#222428`).
- Links: Azul editorial com alto contraste acessível (`#1D4ED8`).

### Edição para Impressão A4 (`-print-a4.pdf`):
- Fundo: Branco puro do papel.
- Texto: Preto sólido (`#000000`).
- Elementos gráficos e quadros: Cinza neutro suave (`gray!6`) com bordas nítidas de 0.7pt.

### Edições para Kindle (`-kindle.pdf` e `-kindle.epub`):
- Otimizadas para telas monocromáticas E-Ink de 16 níveis de cinza.
- Borda de caixas com espessura reforçada (3pt à esquerda) e fundos levemente acinzentados (`#F5F5F5`).

---

## 4. Tipografia Ergonômica para Kindle (`ZERO_MICROFONTS`)

1. **Proibição de Microfontes:**
   - Nunca reduza o tamanho da fonte (ex.: 5pt, 7pt) para espremer uma página inteira de scan original em uma página do Kindle.
   - O corpo do texto no Kindle PDF deve ser de **10pt a 10.5pt** vetorial nativo.
2. **Fluxo Natural Contínuo:**
   - 1 página densa do livro físico (A4/B5) distribui-se naturalmente em **2 a 2.5 páginas Kindle**.
   - As quebras de página ocorrem organicamente onde a tela termina, sem quebras forçadas a cada página escaneada.
3. **Métrica Áurea de Caracteres por Linha:**
   - Margens de 8mm em tela de 105mm x 140mm resultam em ~50 caracteres por linha, garantindo o conforto visual ideal para telas E-Ink de 6" e 6.8".
