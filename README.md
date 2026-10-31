# 📚 BookForge — Plataforma Unificada de Editoração, Tradução e Restauração de Livros

O **BookForge** é um ecossistema completo para o ciclo de vida editorial de livros digitais e digitalizados. Ele unifica em uma única plataforma modular:
1. **Tradução assistida por IA (Gemini Flash Harness)** com guardrails estritos de zero omissão, fidelidade tipográfica e consistência terminológica.
2. **Restauração e Remasterização de Livros Apenas em Imagem (Scans/Fotocópias)**: limpeza de fundo, desinclinação (*deskew*), recorte automatizado de ilustrações em alta resolução e reconstituição de fórmulas matemáticas em texto vetorial cristalino.
3. **Acervo Isolado por Obra (`library/<book-slug>/`)**: cada livro possui seu próprio ciclo de vida encapsulado (arquivo original, figuras, fontes, estados e distribuições finais).
4. **Repositório Central Reutilizável de Templates (`core/templates/`)**: design system consolidado em **LaTeX** e **Typst**, eliminando redundâncias e padronizando 4 formatos canônicos de publicação.
5. **CLI Unificada (`cli.py`)**: automação completa por linha de comando para compilação, aprimoramento de imagem, extração de figuras e monitoramento de progresso.

---

## 🎯 As Quatro Edições Especializadas por Obra

Cada projeto dentro do BookForge foi projetado para gerar simultaneamente até quatro entregáveis especializados a partir de uma fonte única:

| Formato | Finalidade | Geometria / Resolução | Tipografia & Experiência de Leitura |
| :--- | :--- | :--- | :--- |
| **`*-screen.pdf`** | **Leitura em Telas** (Monitores, Notebooks e Tablets) | `185mm x 260mm` | Coluna única fluida (~66 caracteres por linha), entrelinha 1.22, hiperlinks interativos coloridos e bookmarks hierárquicos completos. |
| **`*-print-a4.pdf`** | **Impressão Física** em papel A4 | `210mm x 297mm` (A4) | Margens assimétricas com medianiz para encadernação (`inner=25mm, outer=20mm`), microtipografia ativada, links monocromáticos neutros para tinta. |
| **`*-kindle.pdf`** | **E-Reader Kindle PDF** (6" e 6.8") | `105mm x 140mm` (Proporção 3:4) | Margens ultra-compactas (7mm), tipografia 10pt proporcional sem necessidade de pinça/zoom, alto contraste monocromático (E-Ink). |
| **`*-kindle.epub`** | **Kindle Refluxável** (*Send to Kindle*, App e E-Readers) | EPUB 3 Semântico | Texto 100% refluxável, compatível com fonte Bookerly, troca dinâmica de tamanho de fonte, suporte nativo a Modo Noturno e dicionário. |

---

## 🛠️ Instalação e Requisitos do Sistema

O BookForge utiliza o gerenciador de pacotes ultrarrápido **`uv`** e motores nativos locais:

### Requisitos:
- **Python**: `>= 3.10` (recomendado Python 3.12).
- **uv**: Instalado no sistema (`winget install astral-sh.uv` ou via PowerShell).
- **Compilador LaTeX**: `tectonic` ou `pdflatex` (MiKTeX / TeXLive).
- **Compilador Typst**: Embutido automaticamente via biblioteca Python `typst` (Rust nativo).

### Configuração Inicial do Ambiente:
```powershell
# Clona ou acessa o repositório
cd C:\Projetos\books

# Cria o ambiente virtual Python 3.12 e instala dependências
uv sync
```

---

## 🚀 Guia de Operação da CLI (`cli.py`)

Todas as operações são executadas de forma simples e determinística através de `cli.py`:

```powershell
# Ativar ou executar via ambiente virtual
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
.venv\Scripts\python.exe cli.py status cegalla-novissima-gramatica
.venv\Scripts\python.exe cli.py status historia-da-computacao
```

### 3. Compilar Entregáveis (`build`)
Dispara o motor de compilação correspondente (`typst` ou `latex`) para gerar os formatos finais:
```powershell
# Compilar versão para telas
.venv\Scripts\python.exe cli.py build <slug> --target screen

# Compilar versão para impressão física A4
.venv\Scripts\python.exe cli.py build <slug> --target print

# Compilar edições Kindle (PDF 3:4 E-Ink e Kindle EPUB)
.venv\Scripts\python.exe cli.py build <slug> --target kindle

# Compilar todos os 4 formatos de uma vez
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

### 5. Renderização de Páginas sob Demanda (`render-pages`)
Para livros escaneados em imagem, renderiza páginas específicas em PNG de alta resolução para transcrição:
```powershell
.venv\Scripts\python.exe cli.py render-pages <slug> --start 1 --end 25 --dpi 160
```

### 6. Aprimoramento e Restauração de Imagens (`enhance`)
Executa desinclinação automática (*deskew*) e eliminação de manchas/sombras de lombada nas páginas renderizadas:
```powershell
.venv\Scripts\python.exe cli.py enhance <slug> --deskew --clean
```

### 7. Extração de Figuras de Alta Resolução (`extract-figures`)
Extrai todas as imagens originais incorporadas no PDF sem perdas para `assets/figures/`:
```powershell
.venv\Scripts\python.exe cli.py extract-figures <slug>
```

---

## 📁 Arquitetura de Diretórios

```text
books/
├── cli.py                         # Interface de Linha de Comando central
├── pyproject.toml                 # Configuração uv e dependências
├── uv.lock                        # Lockfile determinístico
├── AGENTS.md                      # Agent Harness para agentes Gemini Flash
├── README.md                      # Esta documentação mestre
├── .gitignore                     # Filtros para ignorar saídas, scans pesados e temporários
├── .agents/                       # Regras e habilidades para agentes de IA
│   ├── rules/
│   │   ├── editorial-design.md    # Regras de design editorial (LaTeX e Typst)
│   │   └── image-enhancement.md   # Diretrizes de restauração e deskew
│   └── skills/
│       ├── translate-book/        # Runbook de tradução em micro-lotes
│       └── image-book-remaster/   # Runbook de conversão de scans para vetor
├── core/                          # Núcleo compartilhado reutilizável
│   ├── templates/
│   │   ├── latex/                 # Preâmbulos e templates LaTeX compartilhados
│   │   ├── typst/                 # Design system e macros Typst compartilhadas
│   │   ├── epub/                  # Folhas de estilo CSS semânticas para Kindle
│   │   └── config/                # Templates de configuração (book.yaml, glossary.json)
│   ├── engines/                   # Motores de compilação (LaTeX, Typst, Kindle Scaler, EPUB)
│   ├── image_pipeline/            # Processamento de imagem (deskew, binarização, extração)
│   └── state_manager.py           # Gestão unificada de estado e manifesto
├── library/                       # Obras organizadas (isolamento estrito)
│   ├── cegalla-novissima-gramatica/
│   ├── matematica-para-vencer/
│   ├── historia-da-computacao/
│   ├── ai-native-software-engineering/
│   └── writing-guide-with-handbook/
└── archive_legacy/                # Cópia segura dos projetos legados originais
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
│   ├── PROGRESS.md                # Dashboard legível
│   └── glossary.json              # Glossário terminológico da obra
└── dist/                          # Entregáveis finais compilados (Screen, Print, Kindle)
```

---

## 🎨 Como Reutilizar os Templates Centrais

### Em Obras Baseadas em LaTeX:
O arquivo mestre local (`source/book-screen.tex`) importa o preâmbulo central via `\input`:
```latex
\documentclass[11pt,oneside,openany]{book}
\input{../../core/templates/latex/template-screen.tex}

\begin{document}
\pagenumbering{arabic}
\input{chapters/00-preliminares.tex}
\tableofcontents
\clearpage

\input{chapters/01-capitulo-01.tex}
% ...
\end{document}
```

### Em Obras Baseadas em Typst:
O arquivo mestre local (`source/main.typ`) importa as macros centrais:
```typst
#import "../../core/templates/typst/template-screen.typ": *

#show: doc => setup-screen(doc, book-title: "Minha Obra", book-author: "Nome do Autor")

// Inclusão modular das páginas ou capítulos
#include "pages/page_0001.typ"
#include "pages/page_0002.typ"
```

---

## 🛡️ Contribuição e Qualidade

Qualquer modificação no código-fonte dos livros deve seguir rigorosamente as diretrizes descritas em [`AGENTS.md`](file:///c:/Projetos/books/AGENTS.md), especialmente a política de **Zero Omissão (`ZERO_TRUNCATION`)** e a remoção completa de elementos repetitivos de cabeçalho e rodapé do original.
