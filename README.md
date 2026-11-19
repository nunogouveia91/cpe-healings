# CPE Auto-Healing Dashboard

Dashboard HTML (ficheiro único, dark theme) que documenta as regras de auto-healing dos CPEs NOS, um modelo por manifesto:
Hitron Hub 5, Sagem FAST 5657, FAST 5670, FAST 3896-15, Strong GN630VE e Askey TCG310J.

## Correr

### Windows: duplo clique

Faz duplo clique em `iniciar.cmd` para iniciar o servidor HTTP na porta **13002**,
acessível pela intranet. O lançador entra na pasta do projeto e executa
`python3 -u .\serve.py` (usa `py -3` ou `python` se `python3` não estiver disponível).
Requer Python 3, sem dependências externas.
Mantém a janela aberta enquanto quiseres disponibilizar o dashboard.

Se descarregares o ZIP do GitHub, extrai primeiro a pasta completa; mantém o
`iniciar.cmd` junto do `index.html` e do `serve.py`. Para iniciar automaticamente
ao entrar no Windows, coloca um **atalho** para o `iniciar.cmd` na pasta Arranque
(`Win+R` → `shell:startup`), não uma cópia do script.

Abre `http://localhost:13002` no servidor ou `http://<ip-do-servidor>:13002`
noutra máquina da intranet. A firewall do servidor tem de permitir ligações TCP
de entrada nessa porta a partir da intranet.

Para outra porta: `iniciar.cmd 13099`. Para abrir apenas o ficheiro local,
sem servidor nem acesso pela rede, abre diretamente o `index.html`.

### Servidor HTTP pela linha de comandos

```powershell
python serve.py          # porta 13002 (0.0.0.0 → também 127.0.0.1 / localhost / IP da máquina)
python serve.py 13099    # outra porta
```

Abrir `http://localhost:13002` ou `http://<ip-do-servidor>:13002`. Só usa a biblioteca standard do Python.

## Regenerar o `index.html`

```powershell
python gen.py
```

- Lê os manifestos `.txt` (separador `€` ou `@`) da pasta `HEALINGS_DIR`
  (por omissão `OneDrive - NOS SGPS, S.A\NOS\healings`).
- Descrições do Hub 5 / FAST 5657 vêm de `base_models.json`; as dos restantes modelos estão no próprio `gen.py`.
- Só substitui os blocos de dados (`modelsMeta`, `database`, `manifestLines`); alterações à UI no `index.html` são preservadas.
- Falha se alguma linha do manifesto não tiver regra correspondente no dashboard.

## Ficheiros

| Ficheiro | Descrição |
|---|---|
| `index.html` | Dashboard |
| `iniciar.cmd` | Lançador Windows do servidor HTTP (requer Python 3) |
| `serve.py` | Servidor HTTP (serve só o `index.html`) |
| `gen.py` | Gerador a partir dos manifestos |
| `base_models.json` | Metadados e descrições base do Hub 5 e FAST 5657 |
