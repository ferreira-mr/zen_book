# AGENTS.md — BookForge Agent Harness (Gemini Flash Optimized)

Este arquivo define o **Agent Harness** (protocolo operacional determinístico, guardrails inegociáveis de qualidade, regras tipográficas e procedimentos para agentes autônomos) para qualquer IA atuando neste repositório.

---

## 1. Princípios Inegociáveis (Hard Guardrails)

Todo agente de IA que atua no BookForge **DEVE** seguir rigorosamente estes princípios:

1. **Zero Omissão / Zero Resumo (`ZERO_TRUNCATION`)**
   - **NUNCA** resuma, abrevie, sintetize, corte parágrafos ou use marcadores de preguiça como `[... restante do texto ...]`, `[continua]` ou `% traduzir depois`.
   - Cada parágrafo, exercício, nota de rodapé, legenda de figura, objetivo pedagógico, apêndice e referência bibliográfica presente no original **deve** constar integralmente no documento final.

2. **Fidelidade aos Títulos Originais (`NO_ARTIFICIAL_LABELS`)**
   - **NUNCA** adicione prefixos genéricos inventados como `"Nota:"`, `"Dica:"`, `"Aviso:"` ou emojis (`ℹ️`, `💡`, `⚠️`) antes de títulos que já existem no livro original.
   - *Exemplo PROIBIDO:* Transformar `LEARNING OUTCOMES` em `Nota: **Objetivos de Aprendizagem**`.
   - *Exemplo CORRETO:* Usar exclusivamente o título original traduzido dentro do ambiente correspondente (`\begin{learningoutcomes}` ou `#feature-box(title: "Objetivos de Aprendizagem")`).

3. **Páginas Limpas de Chrome (`CLEAN_PAGE_CHROME`)**
   - Remova 100% dos cabeçalhos repetitivos do original (como títulos de capítulo redundantes e URLs promocionais do tipo *"Access for free at openstax.org"*).
   - Nos PDFs finais gerados (em todas as edições: Tela, Impressão A4 e Kindle):
     - **Cabeçalho:** Totalmente limpo (`header: none`).
     - **Rodapé:** Contém exclusivamente o número da página no canto inferior direito.

4. **Tipografia Fluida para Kindle — Proibição de Microfontes (`ZERO_MICROFONTS` / `FLUID_KINDLE`)**
   - **JAMAIS** tente forçar 1 página do original denso (A4 ou B5) a caber em 1 única página do Kindle usando fontes minúsculas (5pt a 7pt).
   - No Kindle (PDF e EPUB), o texto **deve fluir naturalmente** de forma contínua: uma página densa original distribui-se organicamente em **2 a 2.5 páginas Kindle**.
   - A fonte base do Kindle PDF deve ser de **10pt a 10.5pt** vetorial nativa, com entrelinha `0.65em` (1.45x) e margens de 8mm, garantindo a média de 48–55 caracteres por linha (conforto visual áureo para telas E-Ink de 6" e 6.8").

5. **Trabalho em Micro-Lotes (`MICRO_CHUNKED_EXECUTION`)**
   - O modelo **JAMAIS** deve tentar processar um capítulo longo (20 a 50 páginas) em uma única operação.
   - Processe sempre **seção por seção** ou **lotes de 3 a 4 páginas por chamada de ferramenta** usando `write_file` (com `Append: true` para seções subsequentes no mesmo arquivo).
   - Valide a compilação com frequência (`.venv\Scripts\python.exe cli.py build <slug>`) para detectar e corrigir erros imediatamente.

6. **Higiene do Repositório (`CLEAN_REPOSITORY`)**
   - O repositório no Git versiona **apenas o framework, motores, templates, ferramentas CLI, regras de agentes e o livro modelo aberto (`library/exemplo-livro-modelo`)**.
   - Arquivos originais de entrada (`original/`), entregáveis compilados (`dist/`) e cache de imagens (`intermediate/`) são mantidos apenas na máquina local.
   - **NUNCA** utilize `git add -f` para forçar o rastreamento de arquivos ignorados. Respeite as regras do `.gitignore`.

7. **Consistência Terminológica (`GLOSSARY_FIRST`)**
   - Antes de traduzir ou revisar capítulos, consulte e alimente `library/<slug>/state/glossary.json` com termos técnicos e decisões de estilo.

8. **Restauração Vetorial de Livros Escaneados (`IMAGE_BOOK_RESTORATION`)**
   - Scans nunca devem ser convertidos em texto corrido sem estrutura.
   - Utilize a visão computacional do modelo para identificar e codificar:
     - Fórmulas matemáticas -> sintaxe Typst `$ ... $` ou LaTeX `\begin{equation}`.
     - Versaletes (*Small Caps*) -> `#smallcaps(...)` ou `\textsc{...}`.
     - Itálicos para termos estrangeiros e citações.
     - Tabelas reais com linhas divisórias limpas.
     - Ilustrações e diagramas recortados em alta resolução (`assets/figures/`).

9. **Imutabilidade de Código e Sintaxe Técnica**
   - Comandos de terminal, variáveis, nomes de funções, palavras-chave de linguagens de programação e URLs **não devem ser traduzidos**. Apenas comentários internos e textos explicativos devem ser vertidos para `pt-BR`.

---

## 2. Padrões de Diagramação Multi-Formato e Nomenclatura

Cada obra no BookForge é compilada a partir de sua fonte modular para até quatro entregáveis especializados em `library/<slug>/dist/`, **nomeados obrigatoriamente no padrão canônico com título da obra e autor**:
`{Título} ({Autor}) - {Edição}.{ext}`

| Elemento no Livro Original | Edição Tela (`*- Screen.pdf`) | Edição Impressão (`*- Print-A4.pdf`) | Edição Kindle PDF (`*- Kindle.pdf`) | Edição Kindle EPUB (`*- Kindle.epub`) |
| :--- | :--- | :--- | :--- | :--- |
| **Padrão em `dist/`** | `{Título} ({Autor}) - Screen.pdf` | `{Título} ({Autor}) - Print-A4.pdf` | `{Título} ({Autor}) - Kindle.pdf` | `{Título} ({Autor}) - Kindle.epub` (e `.azw3`) |
| **Geometria** | `185mm x 260mm` | `210mm x 297mm` (A4) | `105mm x 140mm` (Proporção 3:4) | Refluxável (sem dimensões fixas) |
| **Margens** | Simétricas (22mm) | Com medianiz (`inner=25, outer=20`) | 8mm laterais / 9mm verticais | Controladas pelo leitor |
| **Tamanho da Fonte** | `11pt` (Palatino / Georgia) | `10.5pt` (Palatino / Georgia) | `10.5pt` (Alto contraste E-Ink) | Refluxável (Bookerly padrão) |
| **Entrelinha / Parágrafo** | Entrelinha 1.22, parskip 0.6em | Entrelinha 1.15, parindent 1.25em | Entrelinha 1.45 (`0.65em`), spacing `0.8em` | CSS Bookerly 1.45 |
| **Hiperlinks** | Azuis interativos clicáveis | Preto neutro para tinta de impressão | Monocromático sem molduras | `<a href="...">` nativo |
| **Caixas Pedagógicas** | Fundo suave, borda azul/vinho | Fundo cinza suave, borda nítida | Alto contraste P&B E-Ink | `<aside class="kindle-box">` |
| **Cabeçalho** | Totalmente vazio | Totalmente vazio | Totalmente vazio | Nativo do Kindle |
| **Rodapé** | Apenas número da página à direita | Apenas número da página à direita | Apenas número da página à direita | Nativo do Kindle |

---

## 3. Guia de Sintaxe para Tradução em LaTeX

Ao gerar capítulos em LaTeX (`library/<slug>/source/chapters/XX-capitulo.tex`):

### 3.1. Escapamento Rigoroso de Caracteres Especiais
- `%` $\to$ `\%`
- `&` $\to$ `\&`
- `#` $\to$ `\#`
- `$` $\to$ `\$` (quando for símbolo monetário; em fórmulas matemáticas use `$x^2$`)
- `_` $\to$ `\_` (quando for sublinhado de texto; em índices matemáticos use `$x_1$`)

### 3.2. Ambientes de Caixas e Destaques
- **Objetivos de Aprendizagem:**
  ```latex
  \begin{learningoutcomes}
  Ao final desta seção, você será capaz de:
  \begin{itemize}
    \item Identificar os conceitos...
  \end{itemize}
  \end{learningoutcomes}
  ```
- **Quadro com Título Próprio do Livro:**
  ```latex
  \begin{featurebox}{Título Original Traduzido}
  Conteúdo do quadro sem prefixos artificiais...
  \end{featurebox}
  ```
- **Amostra de Texto / Citação Longa:**
  ```latex
  \begin{sampletext}
  Trecho analisado ou citação direta em destaque...
  \end{sampletext}
  ```
- **Nota Analítica:**
  ```latex
  \begin{analysisnote}
  Comentário explicativo sobre a amostra...
  \end{analysisnote}
  ```

---

## 4. Guia de Sintaxe para Livros em Typst

Ao transcrever livros escaneados em Typst (`library/<slug>/source/pages/page_XXXX.typ`):

### 4.1. Ancoragem de Página Original
Cada página transcrita deve iniciar com o marcador de página original do livro físico:
```typst
#book-page(NUMERO_DA_PAGINA, section: "TITULO_DA_SECAO")
```

### 4.2. Fórmulas Matemáticas Nativas
Converta equações rasterizadas para tipografia vetorial nativa do Typst:
- Frações: `$ frac(a, b) $`
- Potências e Raízes: `$ x^2 + sqrt(y) $`
- Matrizes e Sistemas: `$ mat(1, 2; 3, 4) $`
- Conjuntos: `$ A union B sect C subset.eq D $`

### 4.3. Caixas, Seções e Banners
- Seção numerada: `#sec("1", "CONCEITO FUNDAMENTAL")`
- Abertura de Grande Parte: `#part-banner("I", "FONÉTICA")`
- Observações pedagógicas: `#feature-box(title: "Observação")[Texto...]`
- Figuras recortadas: `#book-fig("assets/figures/fig_01.png", caption: "Legenda original")`

### 4.4. Prevenção de Incompatibilidades no Typst
- **Notas de Rodapé em Tabelas:** Evite usar `#footnote(...)` dentro de `#grid` ou `#table` que atravessem quebra de página (isso causa erro de fechamento de tags no compilador). Em caixas ou tabelas, use texto atenuado `#text(size: 8.5pt, fill: rgb("#555555"))[(Nota: ...)]`.
- **Imports:** Páginas individuais (`page_XXXX.typ`) devem importar o template via `#import "../template.typ": *`. O compilador Typst é configurado com a raiz do projeto (`BASE_DIR`), garantindo resolução de templates compartilhados em `core/templates/typst/`.

---

## 5. Procedimentos Operacionais para o Agente (Runbooks)

### Runbook A: Iniciar uma Nova Obra
```powershell
# 1. Criar a estrutura padronizada
.venv\Scripts\python.exe cli.py init <slug> --file "caminho/arquivo.pdf" --title "Título da Obra" --author "Autor" --engine typst --mode transcribe-image

# 2. Consultar status
.venv\Scripts\python.exe cli.py status <slug>
```

### Runbook B: Processar Livro Escaneado (Motor Typst)
1. **Renderizar lote de páginas:**
   ```powershell
   .venv\Scripts\python.exe cli.py render-pages <slug> --start 1 --end 20 --dpi 160
   ```
2. **Executar aprimoramento e deskew nas imagens:**
   ```powershell
   .venv\Scripts\python.exe cli.py enhance <slug> --deskew --clean
   ```
3. **Extrair ilustrações incorporadas:**
   ```powershell
   .venv\Scripts\python.exe cli.py extract-figures <slug>
   ```
4. **Transcrever página a página via leitura multimodal:**
   - Criar `library/<slug>/source/pages/page_XXXX.typ`.
   - Transcrever todo o conteúdo (textos, fórmulas, versaletes, tabelas).
   - NUNCA usar `#set text(size: ...)` para espremer a página.
5. **Atualizar estado:**
   - Atualizar `library/<slug>/state/manifest.json`.
   - Executar `cli.py status <slug>` para sincronizar o progresso.
6. **Compilar e validar:**
   ```powershell
   .venv\Scripts\python.exe cli.py build <slug> --target screen
   .venv\Scripts\python.exe cli.py build <slug> --target kindle
   ```

### Runbook C: Traduzir Obra Digital (Motor LaTeX)
1. Consultar e padronizar termos técnicos em `library/<slug>/state/glossary.json`.
2. Ler a seção original do livro em `original/`.
3. Traduzir em micro-lotes para `library/<slug>/source/chapters/XX-nome.tex`.
4. Validar a compilação:
   ```powershell
   .venv\Scripts\python.exe cli.py build <slug> --target all
   ```

---

## 6. Comandos de Linha de Comando para o Agente

O agente deve usar **exclusivamente** o ambiente virtual `.venv` para executar tarefas:

```powershell
# Listar obras e status geral
.venv\Scripts\python.exe cli.py list

# Consultar status detalhado de uma obra
.venv\Scripts\python.exe cli.py status <slug>

# Compilar formatos específicos
.venv\Scripts\python.exe cli.py build <slug> --target screen
.venv\Scripts\python.exe cli.py build <slug> --target print
.venv\Scripts\python.exe cli.py build <slug> --target kindle
.venv\Scripts\python.exe cli.py build <slug> --target all

# Conversão e Transferência para Kindle
.venv\Scripts\python.exe cli.py convert-azw3 <slug>
.venv\Scripts\python.exe cli.py send-kindle <slug> --format both

# Pipeline de Imagens
.venv\Scripts\python.exe cli.py render-pages <slug> --start 1 --end 20 --dpi 160
.venv\Scripts\python.exe cli.py enhance <slug> --deskew --clean
.venv\Scripts\python.exe cli.py extract-figures <slug>
```
