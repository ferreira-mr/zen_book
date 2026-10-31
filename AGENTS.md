# AGENTS.md — BookForge Agent Harness (Gemini Flash Optimized)

Este arquivo define o **Agent Harness** (protocolo operacional determinístico, guardrails inegociáveis de qualidade e regras de diagramação em **LaTeX**, **Typst** e **EPUB 3**) para qualquer agente de IA que atue neste repositório.

---

## 1. Princípios Inegociáveis (Hard Guardrails)

1. **Zero Omissão / Zero Resumo (`ZERO_TRUNCATION`)**
   - **NUNCA** resuma, abrevie, sintetize, pule parágrafos ou use placeholders como `[... restante do texto ...]`, `[continua]` ou `% traduzir depois`.
   - Cada parágrafo, objetivo de aprendizagem, pergunta de discussão, nota de rodapé, legenda de figura, tabela, apêndice, prefácio, referência bibliográfica e exercício do PDF original **deve** estar integralmente presente na versão final.

2. **Fidelidade aos Títulos Originais (`NO_ARTIFICIAL_LABELS`)**
   - **NUNCA** adicione prefixos genéricos inventados como `"Nota:"`, `"Dica:"`, `"Aviso:"` ou emojis (`ℹ️`, `💡`, `⚠️`) antes de títulos que já existem no livro original.
   - *Exemplo PROIBIDO:* Transformar `LEARNING OUTCOMES` em `Nota: **Objetivos de Aprendizagem**`.
   - *Exemplo CORRETO:* Usar exclusivamente o título original traduzido dentro do ambiente correspondente (`\begin{learningoutcomes}` ou `#feature-box(title: "Objetivos de Aprendizagem")`).

3. **Páginas Limpas de Chrome (`CLEAN_PAGE_CHROME`)**
   - Remova 100% dos cabeçalhos repetitivos do original (como títulos de capítulo e URLs promocionais do tipo *"Access for free at openstax.org"*).
   - Nos PDFs finais gerados (em todas as edições: Tela, Impressão A4 e Kindle):
     - **Cabeçalho:** Totalmente limpo.
     - **Rodapé:** Contém exclusivamente o número da página no canto inferior direito.

4. **Trabalho em Micro-Lotes (`MICRO_CHUNKED_EXECUTION`)**
   - O modelo **JAMAIS** deve tentar processar um capítulo longo (ex.: 20 a 30 páginas) em uma única operação de escrita.
   - Sempre processe **seção por seção** ou **lotes de 3 a 4 páginas por operação** com `write_file` (usando `Append: true` para seções subsequentes no mesmo arquivo).
   - Valide a compilação com frequência (`.venv\Scripts\python.exe cli.py build <slug>`) para detectar e corrigir erros de sintaxe imediatamente.

5. **Consistência Terminológica (`GLOSSARY_FIRST`)**
   - Antes de iniciar a tradução ou revisão de uma obra, consulte e alimente `library/<slug>/state/glossary.json` com termos técnicos e decisões de estilo.

6. **Restauração de Livros Apenas em Imagem (`IMAGE_BOOK_RESTORATION`)**
   - Scans antigos nunca devem ser convertidos em texto corrido sem estrutura.
   - Utilize a visão computacional do modelo (leitura multimodal) para identificar:
     - Fórmulas matemáticas -> sintaxe Typst `$ ... $` ou LaTeX `\begin{equation}`.
     - Versaletes (*Small Caps*) para nomes de autores.
     - Itálicos para termos estrangeiros e citações.
     - Tabelas reais com linhas divisórias limpas.
     - Diagramas geométricos e ilustrações recortadas em alta resolução (`assets/figures/`).

7. **Imutabilidade de Código e Sintaxe Técnica**
   - Comandos de terminal, variáveis, nomes de funções, palavras-chave de linguagens de programação e URLs **não devem ser traduzidos**. Apenas comentários internos e textos explicativos devem ser vertidos para `pt-BR`.

---

## 2. Padrões de Diagramação Multi-Formato

Cada obra compilada no BookForge deve satisfazer as seguintes especificações tipográficas:

| Elemento no Livro Original | Edição Tela (`-screen.pdf`) | Edição Impressão (`-print-a4.pdf`) | Edição Kindle PDF (`-kindle.pdf`) | Edição Kindle EPUB (`-kindle.epub`) |
| :--- | :--- | :--- | :--- | :--- |
| **Geometria** | `185mm x 260mm` | `210mm x 297mm` (A4) | `105mm x 140mm` (Proporção 3:4) | Refluxável (sem dimensões fixas) |
| **Margens** | Simétricas (22mm) | Com medianiz (`inner=25, outer=20`) | 7mm em todas as bordas | Controladas pelo leitor |
| **Entrelinha / Parágrafo** | Entrelinha 1.22, parskip 0.6em | Entrelinha 1.15, parindent 1.25em | Entrelinha 1.14, parskip 0.45em | CSS padrão Bookerly 1.45 |
| **Hiperlinks** | Azuis interativos clicáveis | Preto neutro para tinta de impressão | Monocromático sem molduras | `<a href="...">` nativo |
| **Caixas Pedagógicas** | Fundo suave, borda azul/vinho | Fundo cinza suave, borda nítida | Alto contraste P&B E-Ink | `<aside class="kindle-box">` |
| **Cabeçalho** | Totalmente vazio | Totalmente vazio | Totalmente vazio | Nativo do Kindle |
| **Rodapé** | Apenas número da página à direita | Apenas número da página à direita | Apenas número da página à direita | Nativo do Kindle |

---

## 3. Regras de Sintaxe para Tradução em LaTeX

Ao gerar capítulos em LaTeX (`library/<slug>/source/chapters/XX-capitulo.tex`):

### 3.1. Escapamento Rigoroso de Caracteres Especiais:
- `%` -> `\%`
- `&` -> `\&`
- `#` -> `\#`
- `$` -> `\$` (quando for símbolo monetário; em fórmulas matemáticas use `$x^2$`)
- `_` -> `\_` (quando for sublinhado de texto; em índices matemáticos use `$x_1$`)

### 3.2. Ambientes de Caixas e Destaques:
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

## 4. Regras de Sintaxe para Livros em Typst

Ao transcrever livros escaneados em Typst (`library/<slug>/source/pages/page_XXXX.typ`):

### 4.1. Ancoragem de Página:
Cada página transcrita deve iniciar com o marcador de página original:
```typst
#book-page(NUMERO_DA_PAGINA, section: "TITULO_DA_SECAO")
```

### 4.2. Fórmulas Matemáticas Nativas:
Converta equações rasterizadas para tipografia vetorial nativa do Typst:
- Frações: `$ frac(a, b) $`
- Potências e Raízes: `$ x^2 + sqrt(y) $`
- Matrizes e Sistemas: `$ mat(1, 2; 3, 4) $`
- Conjuntos: `$ A union B sect C subset.eq D $`

### 4.3. Caixas e Seções:
- Seção numerada: `#sec("1", "CONCEITO FUNDAMENTAL")`
- Abertura de Parte: `#part-banner("I", "FONÉTICA")`
- Observações pedagógicas: `#feature-box(title: "Observação")[Texto...]`

---

## 5. Comandos de Linha de Comando para o Agente

O agente deve usar exclusivamente o ambiente virtual `.venv` para executar tarefas:

```powershell
# 1. Listar obras e status geral
.venv\Scripts\python.exe cli.py list

# 2. Consultar status e progresso de uma obra específica
.venv\Scripts\python.exe cli.py status <slug>

# 3. Compilar formatos
.venv\Scripts\python.exe cli.py build <slug> --target screen
.venv\Scripts\python.exe cli.py build <slug> --target print
.venv\Scripts\python.exe cli.py build <slug> --target kindle
.venv\Scripts\python.exe cli.py build <slug> --target all

# 4. Renderizar páginas de scan sob demanda
.venv\Scripts\python.exe cli.py render-pages <slug> --start 1 --end 20 --dpi 160

# 5. Aprimorar imagens de páginas (deskew e limpeza)
.venv\Scripts\python.exe cli.py enhance <slug> --deskew --clean

# 6. Extrair figuras do PDF original
.venv\Scripts\python.exe cli.py extract-figures <slug>
```
