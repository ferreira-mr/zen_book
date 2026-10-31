# Diretrizes de Aprimoramento e Restauração de Livros em Imagem

Este documento orienta o agente na restauração de scans antigos e fotocópias de livros que não possuem camada de texto digital.

---

## 1. Diagnóstico do Scan Original

Antes de iniciar a transcrição de um livro em imagem:
1. **Verifique se há camada de texto:**
   Execute uma inspeção rápida com PyMuPDF. Se o total de caracteres for próximo de 0, a obra é 100% rasterizada.
2. **Identifique a resolução e inclinação (*skew*):**
   Renderize uma amostra das páginas 15 a 20 em 160 DPI para conferir nitidez, contraste e se as linhas de texto estão inclinadas.
3. **Mapeamento de Páginas:**
   Cruze a numeração do PDF com a numeração impressa no livro físico (identificando capas, folhas de rosto e duplicatas de scanner).

---

## 2. Pipeline de Processamento de Imagens

1. **Desinclinação Automática (*Deskew*):**
   Utilize o comando:
   ```powershell
   .venv\Scripts\python.exe cli.py enhance <slug> --deskew
   ```
   Isso ajusta a rotação das páginas para 0.0° usando a transformada morfológica e mínimos retângulos de contorno.

2. **Limpeza de Fundo e Remoção de Sombras de Lombada:**
   Utilize o comando:
   ```powershell
   .venv\Scripts\python.exe cli.py enhance <slug> --clean
   ```
   Isso divide a imagem pelo modelo de iluminação estimado, eliminando o degradê escuro típico da lombada de livros volumosos.

3. **Recorte Cirúrgico de Ilustrações:**
   - Não recorte manchas ou bordas pretas de digitalização.
   - Isole apenas mapas, fotos, esquemas anatômicos ou diagramas geométricos genuínos na pasta `assets/figures/`.

---

## 3. Vetorização Fiel com Visão Multimodal

Ao transcrever o conteúdo de uma página escaneada para Typst ou LaTeX:
- **Fórmulas e Equações:** NUNCA recorte equações matemáticas como imagens. Transcreva-as para fórmulas vetoriais nativas (`$ frac(a, b) $` ou `\frac{a}{b}`).
- **Tabelas Complexas:** Recrie as tabelas com linhas divisórias limpas (`#table(...)` ou `booktabs`).
- **Versaletes (*Small Caps*):** Nomes de autores em caixas altas de menor tamanho devem usar `#smallcaps("Autor")` ou `\textsc{Autor}`.
