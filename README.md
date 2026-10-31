# 📚 BookForge — Plataforma Editorial Unificada de Tradução, Restauração e Conversão de Livros

O **BookForge** é um ecossistema completo para o ciclo de vida editorial de livros digitais e digitalizados. Ele unifica em uma única plataforma modular:

1. **Tradução assistida por IA (Gemini Flash Harness)** com guardrails estritos de zero omissão, fidelidade tipográfica e consistência terminológica.
2. **Restauração e Remasterização de Livros Apenas em Imagem (Scans/Fotocópias)**: limpeza de fundo, desinclinação (*deskew*), recorte automatizado de ilustrações em alta resolução e reconstituição de fórmulas matemáticas em tipografia vetorial nativa.
3. **Leitura Ergonômica Especializada para Amazon Kindle**: geração de PDF Kindle nativo fluido (10.5pt, proporção 3:4, fluxo contínuo) e EPUB 3 semântico refluxável com Bookerly CSS, eliminando o problema de fontes microscópicas em telas E-Ink.
4. **Repositório Central Reutilizável de Templates (`core/templates/`)**: design system consolidado em **LaTeX** e **Typst**, eliminando redundâncias e padronizando 4 formatos canônicos de publicação.
5. **Acervo Encapsulado por Obra (`library/<book-slug>/`)**: cada livro possui seu próprio ciclo de vida isolado (arquivo original, figuras, fontes, estados e distribuições finais).
6. **Proteção Rigorosa de Direitos Autorais**: o repositório Git público versiona exclusivamente o código do motor, ferramentas e templates; todas as obras proprietárias e scans pesados permanecem protegidos na sua máquina local.

---

## 🎯 As Quatro Edições Especializadas por Obra

Cada projeto dentro do BookForge foi projetado para gerar simultaneamente até quatro entregáveis especializados a partir de uma fonte única:

| Formato | Finalidade | Dimensões | Tipografia & Experiência de Leitura |
| :--- | :--- | :--- | :--- |
| **`*-screen.pdf`** | **Leitura em Telas** (Monitores, Notebooks e Tablets) | `185mm x 260mm` | Coluna única fluida (~66 caracteres por linha), entrelinha 1.22, hiperlinks interativos coloridos e bookmarks hierárquicos completos. Fundo creme suave (`#FAF8F5`). |
| **`*-print-a4.pdf`** | **Impressão Física** em papel A4 | `210mm x 297mm` (A4) | Margens assimétricas com medianiz para encadernação (`inner=25mm, outer=20mm`), microtipografia ativada, links monocromáticos neutros para tinta. |
| **`*-kindle.pdf`** | **E-Reader Kindle PDF** (6" e 6.8") | `105mm x 140mm` (Proporção 3:4) | **Tipografia fluida 10.5pt vetorial** sem quebras forçadas de página. Margens de 8mm, topo limpo e rodapé com número de página. 1 página densa original distribui-se organicamente em ~2 páginas Kindle. |
| **`*-kindle.epub`** | **Kindle Refluxável** (*Send to Kindle*, App e E-Readers) | EPUB 3 Semântico | Texto 100% refluxável, compatível com fonte Bookerly, suporte nativo a ajuste dinâmico de tamanho de fonte, Modo Noturno e dicionário. |

---

## 🛠️ Instalação e Requisitos do Sistema

O BookForge utiliza o gerenciador de pacotes ultrarrápido **`uv`** e motores nativos locais:

### Requisitos:
- **Python**: `>= 3.10` (recomendado Python 3.12).
- **uv**: Instalado no sistema (`winget install astral-sh.uv` ou via PowerShell).
- **Compilador Typst**: Embutido automaticamente via biblioteca Python `typst` (Rust nativo de altíssima velocidade).
- **Compilador LaTeX** (opcional, para obras em LaTeX): `tectonic` ou `pdflatex` (MiKTeX / TeXLive).

### Configuração Inicial do Ambiente:
```powershell
# 1. Clone ou acesse o repositório
cd C:\Projetos\books

# 2. Crie o ambiente virtual Python 3.12 e instale as dependências
uv sync
```

### Teste Rápido de Instalação (Livro Modelo Aberto):
O repositório já inclui uma obra sintética aberta para validação imediata do ambiente:
```powershell
# Compila todos os 4 formatos do livro modelo em ~2 segundos
.venv\Scripts\python.exe cli.py build exemplo-livro-modelo --target all
```

---

## 🚀 Guia de Operação da CLI (`cli.py`)

Todas as operações são executadas de forma simples e determinística através de `cli.py`:

```powershell
.venv\Scripts\python.exe cli.py <comando> [argumentos]
```

### 1. Listar Acervo da Biblioteca (`list`)
Exibe todas as obras cadastradas, o motor de diagramação, o modo de operação, o percentual de conclusão e os entregáveis gerados em `dist/`:
```powershell
.venv\Scripts\python.exe cli.py list
```

### 2. Consultar Status e Dashboard de uma Obra (`status`)
Mostra a barra de progresso visual, estatísticas de páginas/capítulos e a lista detalhada de arquivos de saída com seus tamanhos:
```powershell
.venv\Scripts\python.exe cli.py status exemplo-livro-modelo
.venv\Scripts\python.exe cli.py status cegalla-novissima-gramatica
```

### 3. Compilar Entregáveis (`build`)
Dispara o motor de compilação correspondente (`typst` ou `latex`) para gerar os formatos finais:
```powershell
# Compilar versão para telas (185x260mm)
.venv\Scripts\python.exe cli.py build <slug> --target screen

# Compilar versão para impressão física A4
.venv\Scripts\python.exe cli.py build <slug> --target print

# Compilar edições Kindle (PDF fluido 10.5pt e EPUB 3 refluxável)
.venv\Scripts\python.exe cli.py build <slug> --target kindle

# Compilar todos os 4 formatos simultaneamente
.venv\Scripts\python.exe cli.py build <slug> --target all
```

### 4. Inicializar um Novo Livro (`init`)
Cria a estrutura de pastas padronizada e o arquivo de metadados `book.yaml`:
```powershell
.venv\Scripts\python.exe cli.py init clean-code `
  --file "C:\Downloads\clean-code.pdf" `
  --title "Clean Code: A Handbook of Agile Software Craftsmanship" `
  --author "Robert C. Martin" `
  --engine typst `
  --mode transcribe-image
```

### 5. Renderização de Páginas de Scan (`render-pages`)
Para livros escaneados em imagem, renderiza páginas específicas em PNG de alta resolução para transcrição:
```powershell
.venv\Scripts\python.exe cli.py render-pages <slug> --start 1 --end 25 --dpi 160
```

### 6. Aprimoramento e Restauração de Imagens (`enhance`)
Executa desinclinação automática (*deskew*) e eliminação de sombras de lombada nas páginas renderizadas:
```powershell
.venv\Scripts\python.exe cli.py enhance <slug> --deskew --clean
```

### 7. Extração de Figuras Incorporadas (`extract-figures`)
Extrai todas as imagens originais incorporadas no PDF sem perdas para `assets/figures/`:
```powershell
.venv\Scripts\python.exe cli.py extract-figures <slug>
```

---

## 📱 Motor Especializado Kindle (PDF Fluido & EPUB 3)

Telas E-Ink de 6" e 6.8" (Kindle Paperwhite, Basic e Oasis) possuem requisitos ergonômicos específicos. O BookForge conta com o motor `core/engines/typst_kindle_builder.py`:

- **Tipografia Fluida Nativa (10.5pt):** Elimina a necessidade de forçar 1 página do original em 1 página do Kindle. O texto flui continuamente com tamanho de fonte confortável e legível sem pinça/zoom.
- **Proporção Áurea de Linha:** Largura de impressão de 89mm (após margens de 8mm) acomodando ~50 caracteres por linha, a faixa ideal recomendada pela tipografia clássica (Robert Bringhurst).
- **Sem Quebras Artificiais:** Uma página densa de exercícios ou gramática divide-se naturalmente em 2 a 2.5 páginas Kindle.
- **Topologia Limpa:** Zero cabeçalhos repetitivos ocupando espaço útil; apenas o número da página no rodapé à direita.
- **EPUB 3 Refluxável:** Gera arquivos `.epub` padrão compatíveis com o serviço *Send to Kindle*, dicionário integrado, marcação de texto e modo noturno.

---

## 📁 Arquitetura do Repositório

```text
books/
├── cli.py                         # Interface de Linha de Comando central
├── pyproject.toml                 # Configuração do projeto e dependências uv
├── uv.lock                        # Lockfile determinístico de pacotes
├── AGENTS.md                      # Agent Harness para agentes Gemini Flash
├── README.md                      # Esta documentação mestre
├── .gitignore                     # Proteção de direitos autorais e isolamento de saídas
├── .agents/                       # Regras e habilidades para agentes de IA
│   ├── rules/
│   │   ├── editorial-design.md    # Regras de design editorial (LaTeX e Typst)
│   │   └── image-enhancement.md   # Diretrizes de restauração e deskew
│   └── skills/
│       ├── translate-book/        # Skill operacional de tradução em micro-lotes
│       └── image-book-remaster/   # Skill de transcrição de scans para vetor
├── core/                          # Núcleo compartilhado reutilizável
│   ├── templates/
│   │   ├── latex/                 # Preâmbulos e templates LaTeX compartilhados
│   │   ├── typst/                 # Design system e macros Typst compartilhadas
│   │   ├── epub/                  # Folhas de estilo CSS semânticas para Kindle
│   │   └── config/                # Modelos de configuração (book.yaml, glossary.json)
│   ├── engines/                   # Motores de compilação (LaTeX, Typst, Kindle Fluido, EPUB)
│   ├── image_pipeline/            # Processamento de imagem (deskew, binarização, extração)
│   └── state_manager.py           # Gestão unificada de estado e manifesto
└── library/                       # Obras organizadas (isolamento estrito)
    ├── .gitkeep                   # Mantém a pasta library/ versionada
    ├── exemplo-livro-modelo/      # Livro modelo sintético (aberto e livre de copyright)
    └── <obras-locais>/            # Livros proprietários (permanecem 100% locais via .gitignore)
```

### Estrutura Interna de Cada Livro (`library/<slug>/`):
```text
library/<book-slug>/
├── book.yaml                      # Metadados: título, autor, motor (typst/latex), modo
├── original/                      # Arquivo original intocado (PDF ou EPUB)
├── assets/
│   └── figures/                   # Ilustrações, fotos e gráficos extraídos em alta resolução
├── intermediate/                  # PNGs temporários de páginas e dumps de OCR de apoio
│   ├── page_images/
│   └── ocr_raw/
├── source/                        # Código-fonte modular (.typ ou .tex)
│   ├── chapters/                  # Capítulos (.tex) OU
│   ├── pages/                     # Páginas (.typ)
│   └── main.typ / book-*.tex      # Arquivo mestre que importa os templates de core/
├── state/                         # Controle de progresso
│   ├── manifest.json              # Manifesto atômico de páginas e capítulos
│   ├── PROGRESS.md                # Dashboard legível de progresso
│   └── glossary.json              # Glossário terminológico da obra
└── dist/                          # Entregáveis finais compilados (Screen, Print, Kindle)
```

---

## 🔒 Proteção de Direitos Autorais e Publicação no GitHub

O BookForge foi desenhado com arquitetura de isolamento para publicação segura em repositórios abertos ou privados no GitHub:

1. **O que Sobe para o GitHub:**
   - Todo o código-fonte da plataforma (`core/`, `cli.py`, `pyproject.toml`).
   - Todos os templates reutilizáveis (LaTeX, Typst, EPUB CSS).
   - Documentação, regras de IA e habilidades (`AGENTS.md`, `.agents/`).
   - O livro modelo de teste (`library/exemplo-livro-modelo/`).
2. **O que Fica Estritamente Local:**
   - **Livros Originais de Entrada:** Pastas `original/`, PDFs e EPUBs brutos.
   - **Livros Compilados de Saída:** Pastas `dist/`, arquivos compilados `.pdf` e `.epub`.
   - **Obras Protegidas por Direitos Autorais:** Obras proprietárias (`library/cegalla*`, `library/matematica*`, etc.) permanecem na sua máquina local, funcionando perfeitamente com a CLI, mas são ignoradas pelo Git.
   - **Imagens Intermediárias de Scanner:** Pastas `intermediate/` e caches de OCR.

### Como Publicar no seu GitHub:
```powershell
# 1. Vincule ao seu repositório remoto no GitHub
git remote add origin https://github.com/<SEU-USUARIO>/<SEU-REPOSITORIO>.git

# 2. Envie o branch principal limpo
git push -u origin main
```

---

## 🛡️ Protocolo para Agentes de IA

Qualquer modificação ou extensão deste repositório por agentes de IA deve seguir rigorosamente o harness detalhado em [`AGENTS.md`](file:///c:/Projetos/books/AGENTS.md):
- **Zero Omissão (`ZERO_TRUNCATION`):** Proibido resumir ou pular qualquer parágrafo ou exercício.
- **Páginas Limpas (`CLEAN_PAGE_CHROME`):** Zero cabeçalhos repetitivos no PDF final; apenas número da página no canto inferior direito.
- **Tipografia Fluida (`ZERO_MICROFONTS`):** Proibido comprimir páginas densas com fontes reduzidas no Kindle.
- **Execução em Micro-Lotes (`MICRO_CHUNKED_EXECUTION`):** Processamento estritamente seção por seção para evitar estouro de contexto e erros de compilação.
