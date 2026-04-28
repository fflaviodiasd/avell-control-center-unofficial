# Avell Control Center (GUI)

O **Avell Control Center** é uma interface gráfica não-oficial premium, construída em PyQt6, projetada para substituir o Control Center original em laptops Avell operando sob Linux. 

O projeto foca em entregar máxima leveza, não exigindo dependências pesadas em tempo de execução, e lendo os dados diretamente do Kernel Linux para máxima performance.

---

## 🌟 Funcionalidades Principais

### 1. Controle Avançado de Iluminação (LEDs)
- **Teclado RGB:** Escolha de cores estáticas precisas usando o espectro completo (via `QColorDialog`) ou aplicação de animações por hardware (Rainbow, Wave, Breathing, Raindrop, Aurora, Ripple, etc.).
- **Lightbar Frontal:** Como as lightbars de alguns modelos Avell/TongFang não possuem chip para efeitos nativos, construímos uma **Engine de Renderização por Software** super leve (`lightbar_anim.py`). Ela emula animações (como Breathing e Rainbow) injetando frames diretos na memória (`sysfs`), pausando instantaneamente quando ocioso para preservar a bateria.
- **Cor Fixa Animada:** Você pode selecionar a sua cor estática favorita e aplicar os efeitos "Breathing" focados apenas na sua cor.

### 2. Dashboard de Monitoramento Nativo 
A aba de monitoramento contém 4 gráficos com design moderno e minimalista desenhados por vetores (`QPainter`), extraindo a telemetria na raiz do Linux:
- **Rede (Mirrored Line Chart):** Mede em tempo real a taxa de *Download* e *Upload* via `/proc/net/dev`, desenhando uma onda viva em verde e roxo com escala adaptativa automática (KB/s para MB/s).
- **CPU (Micro Area Chart):** Lê o `/proc/stat` para extrair os *ticks* do processador e montar uma curva temporal dos núcleos.
- **Memória (Stacked Progress Bar):** Filtra o `/proc/meminfo` calculando a memória cache/buffer e apontando a real memória utilizada.
- **Disco (Donut Chart):** Mede de forma estática o uso da raiz do sistema operacional, exibindo no centro de um "anel".

---

## 🛠️ Como Instalar as Dependências

O uso no Linux requer o *Tuxedo Keyboard* modificado e a interface em Python `aucc`. Para facilitar, criamos um instalador automático.

1. Navegue até a pasta do projeto no seu terminal.
2. Dê permissão de execução aos scripts:
   ```bash
   chmod +x install_deps.sh
   chmod +x install_service.sh
   ```
3. Rode a instalação de dependências fornecendo o nome do seu usuário (para o instalador autorizar os comandos `sudo` visualmente no futuro sem pedir senha no terminal):
   ```bash
   sudo ./install_deps.sh SEU_NOME_DE_USUARIO
   ```
   *Nota: O script fará o download do Git, DKMS, cabeçalhos do Kernel, compiladores, drivers do Tuxedo e o pacote usbutils automaticamente.*

---

## 🚀 Como Executar

Se estiver usando um ambiente virtual (venv), ative-o, ou apenas rode usando a versão padrão (PyQt6 instalado pelo apt):

```bash
python3 main.py
```
> O aplicativo ficará na bandeja do sistema (System Tray) para rodar de fundo.

---

## 📁 Estrutura de Arquivos

- **`main.py`**: Motor gráfico e arquivo principal do PyQt6. Faz as validações da UI e integra as janelas.
- **`monitor_widgets.py`**: Código vetorial cru das classes de gráficos em tempo real (`NetMirroredChart`, `CpuAreaChart`, etc.).
- **`lightbar_anim.py`**: Daemon auxiliar leve em Python invocado apenas quando animações da Lightbar são ligadas.
- **`install_deps.sh`**: Automação bash para o ecossistema Debian/Ubuntu que checa drivers ITE e aplica patches.
- **`installer.py`** / **`install_service.sh`**: Ferramentas auxiliares de configuração de *Auto-start* na inicialização do sistema.

---

## 🤝 Colaborações
O projeto é mantido por entusiastas e usuários de Linux/Avell. Se o seu modelo possui um chip diferente do ITE 8291, basta editar a flag correta no *script* ou nos parâmetros do `aucc`. Pull requests são bem-vindos!
