---
name: translate-book
description: >-
  Pipeline determinístico otimizado para Gemini Flash para traduzir integralmente obras digitais
  (PDF ou EPUB) em micro-lotes para LaTeX modular, gerando 4 saídas finais especializadas
  (Screen PDF, Print A4, Kindle PDF e Kindle EPUB).
---

# Skill: Tradução Integral e Diagramação Multi-Formato (`translate-book`)

Siga este procedimento passo a passo sempre que for requisitada a tradução de uma obra no BookForge.

---

## Passo 1: Inicialização e Verificação de Estado

1. Verifique se o livro está cadastrado na biblioteca:
   ```powershell
   .venv\Scripts\python.exe cli.py status <slug>
   ```
2. Se for uma obra nova, inicialize via CLI:
   ```powershell
   .venv\Scripts\python.exe cli.py init <slug> --file "caminho/original.pdf" --engine latex --mode translate
   ```
3. Consulte `library/<slug>/state/glossary.json` e padronize termos técnicos antes de iniciar a tradução dos capítulos.

---

## Passo 2: Tradução em Micro-Lotes (Seção por Seção)

1. Para cada unidade pendente em `library/<slug>/state/manifest.json`:
   - Traduza em blocos curtos de **1 seção ou no máximo 3 a 4 páginas por vez**.
   - Na primeira seção do capítulo, crie `library/<slug>/source/chapters/XX-nome.tex` com `Overwrite: true`.
   - Nas seções seguintes do mesmo capítulo, grave o conteúdo usando `write_file` com `Append: true`.
2. Respeite os guardrails inegociáveis:
   - Proibido resumir (`ZERO_TRUNCATION`).
   - Proibido prefixos `"Nota:"` antes de títulos existentes.
   - Escapar `%`, `&`, `#`, `$` e `_` no texto em prosa.

---

## Passo 3: Compilação e Entrega das 4 Edições

Após concluir as seções do capítulo, teste a compilação:
```powershell
.venv\Scripts\python.exe cli.py build <slug> --target all
```
Verifique se os 4 entregáveis foram gerados em `library/<slug>/dist/`:
- `<slug>-screen.pdf`
- `<slug>-print-a4.pdf`
- `<slug>-kindle.pdf`
- `<slug>-kindle.epub`
