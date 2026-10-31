---
name: image-book-remaster
description: >-
  Pipeline operacional para remasterização de livros digitalizados apenas em imagem (scans sem OCR).
  Realiza renderização sob demanda, aprimoramento de imagem, extração de figuras e transcrição
  página por página em código Typst 100% vetorial de alta definição.
---

# Skill: Remasterização de Livros em Imagem (`image-book-remaster`)

Siga este procedimento passo a passo sempre que converter um livro escaneado em imagem para edição vetorial cristalina.

---

## Passo 1: Inicialização da Obra e Mapeamento

1. Se for um livro novo:
   ```powershell
   .venv\Scripts\python.exe cli.py init <slug> --file "caminho/scan.pdf" --engine typst --mode transcribe-image
   ```
2. Inspecione o PDF original para definir a correlação `Página_do_PDF` vs. `Página_do_Livro`.
3. Verifique a existência de páginas duplicadas por erro de scanner (ex.: páginas idênticas consecutivas).

---

## Passo 2: Renderização e Aprimoramento de Imagens

1. Renderize o lote de páginas que será trabalhado (ex.: páginas 1 a 20):
   ```powershell
   .venv\Scripts\python.exe cli.py render-pages <slug> --start 1 --end 20 --dpi 160
   ```
2. Execute desinclinação e limpeza de fundo:
   ```powershell
   .venv\Scripts\python.exe cli.py enhance <slug> --deskew --clean
   ```

---

## Passo 3: Transcrição Página por Página em Typst

1. Para cada página do lote:
   - Crie o arquivo `library/<slug>/source/pages/page_XXXX.typ`.
   - Inicie com a âncora `#book-page(NUMERO_LIVRO, section: "TITULO")`.
   - Use leitura multimodal para identificar e transcrever:
     - Textos em negrito, itálico e versaletes (`#smallcaps(...)`).
     - Fórmulas matemáticas em `$ ... $`.
     - Tabelas reais com divisórias limpas.
   - Isole ilustrações em `assets/figures/` e insira com `#book-fig("assets/figures/nome.png")`.
   - **Atenção:** NUNCA force o tamanho da fonte (ex.: `#set text(size: 6pt)`) para espremer conteúdo em 1 página. Deixe o texto fluir livremente.
2. Compile a página ou lote parcial para validar a ausência de erros de sintaxe Typst:
   ```powershell
   .venv\Scripts\python.exe cli.py build <slug> --target screen
   ```

---

## Passo 4: Geração das Saídas Finais (Incluindo Kindle Fluido)

Ao concluir o lote ou o livro:
```powershell
# Compilar edições Kindle ergonômicas (PDF fluido 10.5pt e EPUB 3)
.venv\Scripts\python.exe cli.py build <slug> --target kindle

# Compilar todos os 4 formatos
.venv\Scripts\python.exe cli.py build <slug> --target all
```
Isso gera os entregáveis finais leves (5 a 15 MB) substituindo os scans originais pesados (40 a 600 MB).
