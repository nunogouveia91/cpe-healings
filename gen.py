# -*- coding: utf-8 -*-
import json, re, io, os

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.join(HERE, "index.html")
BASE = os.environ.get("HEALINGS_DIR", r"c:\Users\nanobreg\OneDrive - NOS SGPS, S.A\NOS\healings")

MODELS = [
    ("fast5670", BASE + r"\f5670\check_cpe_health_sagem_fast5670.txt", "\u20ac",
     "Sagemcom FAST 5670", "Sagem FAST 5670", "FTTH / GPON", "GPON / FTTH (xmo-client)"),
    ("fast3896", BASE + r"\sagem hfc\check_cpe_health_sagem_fast3896-15.txt", "@",
     "Sagemcom FAST 3896-15", "Sagem FAST 3896", "HFC / DOCSIS", "DOCSIS / HFC (RDK-B dmcli)"),
    ("gn630ve", BASE + r"\strong\check_cpe_health_gn630ve.txt", "\u20ac",
     "Strong GN630VE", "Strong GN630VE", "FTTH / GPON", "GPON / FTTH (OpenWrt datamodel/ubus)"),
    ("tcg310j", BASE + r"\askey\check_cpe_health_askey.txt", "@",
     "Askey TCG310J", "Askey TCG310J", "HFC / DOCSIS", "DOCSIS / HFC (RDK-B dmcli)"),
]

CAT_ORDER = ["WIFI", "SECURITY", "SYSTEM", "NETWORK", "VOICE", "DOCSIS", "STORAGE", "PON"]

# ---------------------------------------------------------------- bash formatter
PAT = "\x01"  # marks a 'case' pattern token, e.g. "7.3*)"

def split_top(s):
    """Split on top-level ';' (outside quotes, $(...), (...), [[ ]]) and handle '\\' escapes."""
    parts, cur, i, depth, q = [], [], 0, 0, None
    while i < len(s):
        c = s[i]
        if q == "'":
            cur.append(c)
            if c == "'": q = None
        elif q == '"':
            cur.append(c)
            if c == "\\" and i + 1 < len(s):
                cur.append(s[i + 1]); i += 1
            elif c == '"': q = None
        else:
            if c in "'\"":
                q = c; cur.append(c)
            elif c == "\\" and i + 1 < len(s):
                cur.append(c); cur.append(s[i + 1]); i += 1
            elif c in "({":
                depth += 1; cur.append(c)
            elif c in ")}":
                if c == ")" and depth == 0:
                    # unmatched ')' at top level = end of a case pattern
                    cur.append(c + PAT); parts.append("".join(cur)); cur = []
                else:
                    depth -= 1; cur.append(c)
            elif c == "\n" and depth == 0:
                parts.append("".join(cur)); cur = []
            elif c == ";" and depth == 0:
                parts.append("".join(cur)); cur = []
                if i + 1 < len(s) and s[i + 1] == ";":
                    parts.append(";;"); i += 1
            else:
                cur.append(c)
        i += 1
    parts.append("".join(cur))
    return [p.strip() for p in parts if p.strip()]

def fmt_bash(src):
    src = src.strip()
    if not src:
        return ""
    lines, ind = [], 0
    pad = lambda: "  " * ind
    queue = split_top(src)
    while queue:
        st = queue.pop(0).strip()
        if not st:
            continue
        m = re.match(r"^case\s+(.+?)\s+in\s+(.+)$", st, re.S)
        if m:
            lines.append(pad() + f"case {m.group(1)} in")
            ind += 1
            queue.insert(0, m.group(2))
            continue
        if st.endswith(PAT):
            lines.append(pad() + st[:-len(PAT)].strip())
            ind += 1
            continue
        if st == ";;":
            lines.append(pad() + ";;")
            ind = max(ind - 1, 0)
            continue
        if st == "esac":
            ind = max(ind - 1, 0)
            lines.append(pad() + "esac")
            continue
        m = re.match(r"^(then|do|else)\b\s*(.*)$", st, re.S)
        if m:
            kw, rest = m.group(1), m.group(2)
            if kw in ("then", "do"):
                if lines:
                    lines[-1] += "; " + kw
                else:
                    lines.append(kw)
                ind += 1
            else:
                ind = max(ind - 1, 0)
                lines.append(pad() + "else")
                ind += 1
            if rest:
                queue.insert(0, rest)
            continue
        m = re.match(r"^elif\b\s*(.*)$", st, re.S)
        if m:
            ind = max(ind - 1, 0)
            lines.append(pad() + "elif " + m.group(1))
            continue
        m = re.match(r"^(fi|done)\b\s*(.*)$", st, re.S)
        if m:
            ind = max(ind - 1, 0)
            lines.append(pad() + m.group(1))
            if m.group(2):
                queue.insert(0, m.group(2))
            continue
        # inline "while cmd; do :; done" style constructs stay as statements
        lines.append(pad() + st)
    return "\n".join(lines)

# ---------------------------------------------------------------- descriptions
# (category, title, summary, detect, trigger, action)
def eth(n, src):
    return ("NETWORK", f"Degradação de Velocidade na Porta LAN eth{n}",
            "Deteta renegociação da porta Ethernet para uma velocidade inferior (ex.: 1000 → 100 Mbps).",
            f"Lê a velocidade e o estado de eth{n} ({src}) e compara com a última leitura guardada em /tmp/ETH{n}_Speed.",
            "Porta UP E velocidade atual < velocidade da leitura anterior",
            "Sem ação corretiva — apenas monitorização e reporte.")

D = {}
# ---------------- FAST 5670
f = D["fast5670"] = {}
f["disable_ksmbd"] = ("SECURITY", "Desativação de Servidor SMB / KSMBD",
    "Garante que a partilha SMB permanece desligada, reduzindo a superfície de ataque.",
    "Lê StorageService[1]/NetworkServer/SMBEnable via xmo-client.",
    "SMBEnable == true", "Define SMBEnable = false via xmo-client.")
for b, u, iface in (("24", "1", "wl1"), ("5", "2", "wl0")):
    band = "2.4 GHz" if b == "24" else "5 GHz"
    f[f"wifi_radio_{b}_enable"] = ("WIFI", f"Coerência do Rádio {band} vs Estado do SSID",
        f"Deteta o rádio {band} desligado sem que o SSID reflita LOWERLAYERDOWN (estado incoerente).",
        f"Lê Radio[{u}]/Enable e SSID[{u}]/Status via xmo-client.",
        f"Radio[{u}].Enable == false E SSID[{u}].Status != LOWERLAYERDOWN",
        f"Se SSID[{u}].Status == DOWN, reativa SSID[{u}]/Enable = true.")
    f[f"wifi_radio_{b}_status"] = ("WIFI", f"Rádio {band} em Estado Operacional Anómalo",
        f"Rádio {band} configurado como ativo mas em baixo (ou UP estando desativado).",
        f"Cruza Radio[{u}]/Status, Radio[{u}]/Enable e SSID[{u}]/Enable.",
        "(Status == DOWN E Rádio/SSID ativos) OU (Status == UP E Rádio desativado)",
        f"Força Radio[{u}]/Enable e AccessPoint[{u}]/Enable = true.")
    f[f"wifi_ssid_{b}_status"] = ("WIFI", f"Recuperação de SSID {band} Bloqueado",
        f"Corrige o SSID {band} preso em DOWN, DORMANT ou LOWERLAYERDOWN apesar de configurado ativo.",
        f"Lê SSID[{u}]/Status, SSID[{u}]/Enable e Radio[{u}]/Enable.",
        "Estado não coerente (ex.: SSID ativo com Status DOWN/DORMANT/LOWERLAYERDOWN e rádio ativo)",
        f"Reativa SSID[{u}]/Enable e AccessPoint[{u}]/Enable.")
    f[f"wifi_inteface_wlan_{b}_load"] = ("WIFI", f"Interface WLAN {band} ({iface}) Não Carregada",
        f"A interface física {iface} desapareceu do kernel apesar de Rádio e SSID estarem ativos.",
        f"Procura {iface} em ifconfig e lê Radio[{u}]/Enable e SSID[{u}]/Enable.",
        f"{iface} ausente E Radio[{u}] == true E SSID[{u}] == true",
        f"Se AccessPoint ativo: ifconfig {iface} up; caso contrário reativa SSID[{u}] e AccessPoint[{u}].")
for n in range(4):
    f[f"eth{n}_speed"] = eth(n, "/sys/devices/virtual/net")
f["voice_line_status"] = ("VOICE", "Linha de Voz VoIP em Erro",
    "Deteta a linha SIP 1 em estado ERROR, deixando o cliente sem serviço telefónico.",
    "Lê VoiceProfile[1]/Lines/Line[1]/Status via xmo-client.",
    "Line[1].Status == ERROR", "Sem healing live — escala diretamente para reboot.")
f["dhcp_lan_server"] = ("NETWORK", "Servidor DHCP da LAN em Erro",
    "Em modo router, o pool DHCPv4 da LAN entra em ERROR e os clientes deixam de obter IP.",
    "Lê RemoteAccess/BridgeMode/SoftBridge/Enable e DHCPv4 Pool[1]/Status.",
    "Bridge mode desativado E Pool[1].Status == ERROR",
    "Termina o processo dhcpd (pkill) para forçar o seu reinício.")
f["disable_watchdog"] = ("SYSTEM", "Desativação de Watchdog Hardware de Kernel",
    "Previne reinícios espúrios em picos de CPU causados pelo hardware watchdog.",
    "Lê /proc/watchdog/info à procura de 'WD enabled'.",
    "WD enabled presente", "Envia o caractere de controlo 'K' para /proc/watchdog/info.")
f["ipv6_duplicated_leases"] = ("NETWORK", "Prefixos IPv6 Duplicados na Lease DHCPv6",
    "Vários IA_PREFIX distintos na lease do dhclient6 podem quebrar a conectividade IPv6.",
    "Com IPv6 ativo, conta os iaprefix únicos em /tmp/etc/dhclient6_data.leases.",
    "Mais de 1 iaprefix distinto",
    "Limpa o ficheiro de leases e termina o dhclient -6 para renegociar.")
f["ipv6_rebind_renew_eq_zero"] = ("NETWORK", "Lease IPv6 com Temporizador Rebind = 0",
    "Um rebind a zero impede a renovação correta do prefixo IPv6 delegado.",
    "Com IPv6 ativo, procura 'rebind 0' em /tmp/etc/dhclient6_data.leases.",
    "Pelo menos uma entrada 'rebind 0'",
    "Limpa o ficheiro de leases e termina o dhclient6 da interface veip0.11.")
f["pptpvpn_enable"] = ("NETWORK", "PPTP Passthrough Desativado (FW SGFc12000059)",
    "Na versão SGFc12000059 o passthrough PPTP fica desligado e bloqueia VPNs PPTP dos clientes.",
    "Lê DeviceInfo.SoftwareVersion e NAT/PPTPPassthroughEnable.",
    "SW == SGFc12000059 E PPTPPassthroughEnable == false",
    "Ativa NAT/PPTPPassthroughEnable via xmo-client.")
f["conntrack_tcp_timeout_established"] = ("NETWORK", "Timeout de Conntrack TCP Excessivo",
    "Um timeout elevado enche a tabela de conntrack com sessões TCP mortas.",
    "Lê sysctl net.netfilter.nf_conntrack_tcp_timeout_established.",
    "Timeout > 7200 s", "Define o timeout para 3600 s via sysctl -w.")
f["wifi_bandsteering_status"] = ("WIFI", "Band Steering Desativado com SSIDs Unificados",
    "Com 2.4G e 5G com o mesmo SSID, password e segurança, o Smart Handover tem de estar ativo.",
    "Compara SSID, KeyPassphrase e ModeEnabled dos AP 1 e 2; lê SmartHandoverSettings/Enable.",
    "Credenciais iguais E SmartHandover == false",
    "Ativa SmartHandoverSettings/Enable.")
f["unify_wifi_ssid_default_config"] = ("WIFI", "SSIDs de Fábrica Não Unificados",
    "Garante que o SSID de fábrica do 5G é igual ao do 2.4G nos parâmetros persistentes (PP).",
    "Exporta os parâmetros persistentes (get_pp all) e compara WIFI_SSID1 com WIFI_SSID2.",
    "WIFI_SSID1 != WIFI_SSID2",
    "Reescreve WIFI_SSID2 = WIFI_SSID1 e grava com write_pp.sh.")
for b, u in (("24", "1"), ("5", "2")):
    band = "2.4 GHz" if b == "24" else "5 GHz"
    f[f"pckt_loss_conf_{b}"] = ("WIFI", f"Parâmetro ZeroPacketLost {band} (FW SGFc12000065)",
        f"Na versão SGFc12000065 força ZeroPacketLost = 0 no AP {band} para mitigar perda de pacotes.",
        f"Lê DeviceInfo.SoftwareVersion e AccessPoint[{u}]/ZeroPacketLost.",
        "SW == SGFc12000065 E ZeroPacketLost != 0",
        f"Define AccessPoint[{u}]/ZeroPacketLost = 0.")

# ---------------- FAST 3896-15
f = D["fast3896"] = {}
f["disable_ksmbd"] = ("SECURITY", "Desativação de Servidor SMB / KSMBD",
    "Garante que a partilha SMB permanece desligada, reduzindo a superfície de ataque.",
    "Lê Device.Services.StorageService.NetworkServer.SMBEnable via dmcli.",
    "SMBEnable == true", "Define SMBEnable = false via dmcli.")
for b, u, iface in (("24", "1", "wl0"), ("5", "2", "wl1")):
    band = "2.4 GHz" if b == "24" else "5 GHz"
    f[f"wifi_radio_{b}_enable"] = ("WIFI", f"Rádio Wi-Fi {band} Desativado",
        f"Garante que o rádio {band} está ligado.",
        f"Lê Device.WiFi.Radio.{u}.Enable via dmcli.",
        f"Radio.{u}.Enable == false", f"Define Radio.{u}.Enable = true e aguarda 4 s.")
    f[f"wifi_radio_{b}_status"] = ("WIFI", f"Rádio {band} Operacionalmente em Baixo",
        f"Rádio {band} reporta estado Down.",
        f"Lê Device.WiFi.Radio.{u}.Status via dmcli.",
        f"Radio.{u}.Status == Down", f"Reaplica Radio.{u}.Enable = true e aguarda 4 s.")
    f[f"wifi_ssid_{b}_status"] = ("WIFI", f"SSID {band} em Baixo Estando Ativo",
        f"O SSID {band} está configurado ativo mas o estado operacional é Down.",
        f"Lê SSID.{u}.Status e SSID.{u}.Enable via dmcli.",
        f"SSID.{u}.Status == Down E SSID.{u}.Enable == true",
        f"Reaplica Radio.{u}.Enable = true e aguarda 4 s.")
    f[f"wifi_inteface_wlan_{b}_load"] = ("WIFI", f"Interface WLAN {band} ({iface}) Não Carregada",
        f"A interface física {iface} desapareceu do kernel com o SSID ativo.",
        f"Procura {iface} em ifconfig e lê SSID.{u}.Enable.",
        f"{iface} ausente E SSID.{u}.Enable == true",
        f"Reaplica Radio.{u}.Enable = true e aguarda 4 s.")
f["wifi_radio_5_channel_bandwith_status"] = ("WIFI", "Largura de Canal 5 GHz Limitada a 20 MHz",
    "Um canal de 20 MHz no 5G reduz drasticamente o débito Wi-Fi disponível.",
    "Lê Device.WiFi.Radio.2.OperatingChannelBandwidth via dmcli.",
    "OperatingChannelBandwidth == 20MHz", "Define OperatingChannelBandwidth = 80MHz.")
f["disable_upstream_messages"] = ("SYSTEM", "Desativação de Notificações Upstream (Clientes / Presença)",
    "Evita o envio contínuo de notificações de clientes ligados e presença para a cloud.",
    "Lê os atributos (geta) de NotifyComponent Connected-Client e PresenceNotification.",
    "Ambas as notificações com 'notification:on'",
    "Coloca ambas as notificações a off (seta ... off anybody).")
f["wifi_bandsteering_status"] = ("WIFI", "Band Steering Desativado com SSIDs Unificados",
    "Com 2.4G e 5G com o mesmo SSID e segurança, o Band Steering tem de estar ativo.",
    "Compara SSID, ModeEnabled, EncryptionMethod e KeyPassphrase dos AP 1 e 2; lê BandSteering.Enable.",
    "Credenciais iguais E BandSteering.Enable == false",
    "Ativa X_RDKCENTRAL-COM_BandSteering.Enable.")
f["block_local_page_php"] = ("SECURITY", "Bloqueio da Página Local (80/443/6080/4433)",
    "Impede o acesso à interface web local a partir da LAN (br+) e de l2sd0.106.",
    "Valida a cadeia NOS_LOCALPAGE (DROP nas portas 80/443/6080/4433) em iptables e ip6tables, na 1.ª posição do INPUT.",
    "Cadeia ausente, incompleta ou fora da 1.ª posição do INPUT",
    "Recria NOS_LOCALPAGE com as regras DROP e reinsere-a no topo do INPUT.")

# ---------------- GN630VE
f = D["gn630ve"] = {}
for svc, port in (("http", 80), ("https", 443), ("ftp", 21)):
    S = svc.upper()
    f[f"disable_{svc}_wan"] = ("SECURITY", f"Bloqueio de {S} ({port}) na WAN",
        f"Impede que a gestão/serviço {S} fique exposto na interface WAN.",
        f"Procura a regra fw3 'Allow-{S}' com ACCEPT em iptables.",
        f"Regra Allow-{S} ACCEPT presente",
        f"Remove a regra tcp/{port} da chain zone_wan_input (IPv4 e IPv6).")
f["wifi_radio_24_bandwidth"] = ("WIFI", "Largura de Canal 2.4 GHz Inadequada",
    "No 2.4G, 40 MHz/Auto aumenta interferências; a norma é 20 MHz.",
    "Lê Device.WiFi.Radio.1.OperatingChannelBandwidth via datamodel.",
    "Bandwidth == 40MHz OU Auto", "Define OperatingChannelBandwidth = 20MHz.")
f["wifi_radio_5_bandwidth"] = ("WIFI", "Largura de Canal 5 GHz Inadequada",
    "No 5G, 160 MHz/Auto causa instabilidade; a norma é 80 MHz.",
    "Lê Device.WiFi.Radio.2.OperatingChannelBandwidth via datamodel.",
    "Bandwidth == Auto OU 160MHz", "Define OperatingChannelBandwidth = 80MHz.")
for b, u in (("24", "1"), ("5", "2")):
    band = "2.4 GHz" if b == "24" else "5 GHz"
    f[f"wifi_{b}_encryption_mode"] = ("WIFI", f"Encriptação Wi-Fi {band} em Modo Misto TKIP+AES",
        f"O modo TKIPAES degrada o débito e a segurança do Wi-Fi {band}.",
        f"Lê AccessPoint.{u}.Security.EncryptionModeEnable via datamodel.",
        "EncryptionModeEnable == TKIPAES", "Define EncryptionModeEnable = AES.")
f["easycwmp_max_timeout"] = ("SYSTEM", "Timeout de Download TR-069 (easycwmp)",
    "Aumenta o MAX_TIMEOUT dos downloads TR-069 (ex.: firmware) de 180 s para 300 s.",
    "Lê MAX_TIMEOUT em /usr/share/easycwmp/functions/curl_download.",
    "MAX_TIMEOUT != 300", "Se o valor for 180, substitui por 300 via sed.")
f["mem_free_check"] = ("SYSTEM", "Memória RAM Livre Crítica",
    "Pouca memória livre leva a falhas de processos e degradação do serviço.",
    "Lê a memória livre com free.",
    "Memória livre < 150 000 KB", "Sem healing live — escala diretamente para reboot.")
f["disable_smb_service"] = ("SECURITY", "Desativação do Serviço Samba (SMB)",
    "Garante que o serviço samba4 não está a correr no CPE.",
    "Lê o estado de /etc/init.d/samba4.",
    "samba4 == running", "Para e desativa o arranque do samba4.")
f["disable_voip_service"] = ("VOICE", "Desativação de VoIP em Variante sem Voz",
    "Na variante de marca 2 o serviço VoIP não deve correr e a interface IP 8 deve estar ativa.",
    "Lê X_NOS.BrandVariant, o estado de /etc/init.d/voip e IP.Interface.8.Enable.",
    "BrandVariant == 2 E (voip running OU Interface.8.Enable == 0)",
    "Para e desativa o voip e ativa IP.Interface.8.")
f["ssh_port"] = ("SECURITY", "Porta SSH de Gestão Não Standard",
    "Garante que o acesso SSH remoto usa a porta de gestão 10022.",
    "Lê Device.Services.RemoteAccess.SSHPort via datamodel.",
    "SSHPort != 10022", "Define SSHPort = 10022.")
f["disable_zz_config_inotify"] = ("SYSTEM", "Processo zz_config_inotify Ativo",
    "Desliga o observador de configuração zz_config_inotify, que não deve correr em produção.",
    "Procura o processo zz_config_inotify em top.",
    "Processo em execução", "Para e desativa o serviço zz_config_inotify.")
f["dns_local_answer_fix"] = ("NETWORK", "DNS Local Sem Resposta",
    "O resolver local (dnsmasq) deixa de responder e os clientes ficam sem navegação.",
    "Resolve api.clg.nos.pt com nslookup.",
    "Sem endereço resolvido", "Reinicia o dnsmasq.")
f["hw_nat"] = ("NETWORK", "Parametrização de Aceleração HW NAT",
    "Garante que os timeouts de HW NAT são aplicados após cada arranque.",
    "Lê o marcador /tmp/hw_nat.",
    "Marcador != 2 (parâmetros ainda não aplicados)",
    "Aplica hw_nat -N 30, -T 3, -U 60 60 15 60 e grava o marcador 2.")
f["dns_cache"] = ("NETWORK", "Tamanho da Cache DNS",
    "Garante uma cache DNS de 200 entradas no dnsmasq.",
    "Lê Device.DNS.cachesize via datamodel.",
    "cachesize != 200", "Define cachesize = 200.")
f["ipv6_disabled_status"] = ("NETWORK", "IPv6 Desativado na WAN",
    "A WAN deve operar em dual-stack (IPStack = 1).",
    "Lê IPStack da WAN 1 via ubus gwweb.wancfg getWanCfg.",
    "IPStack != 1",
    "Reaplica a configuração WAN (DHCP, VLAN 11, NAT, IPStack = 1) via ubus.")
for b, u, o, ou, iface in (("24", "1", "5", "2", "ra0"), ("5", "2", "24", "1", "rai0")):
    band = "2.4 GHz" if b == "24" else "5 GHz"
    oband = "2.4 GHz" if o == "24" else "5 GHz"
    f[f"wifi_radio_{b}_status"] = ("WIFI", f"Rádio {band} Desligado com {oband} Ligado",
        f"Deteta o rádio {band} desligado isoladamente, mantendo apenas o {oband}.",
        f"Lê Radio.1.Enable e Radio.2.Enable via datamodel.",
        f"Radio.{u}.Enable == 0 E Radio.{ou}.Enable == 1",
        f"Ativa Radio.{u} e recarrega o Wi-Fi (ubus rtweb.wifi reload).")
    f[f"wifi_ssid_{b}_status"] = ("WIFI", f"SSID {band} Desligado em Rede Unificada",
        f"Com SSIDs iguais, o SSID {band} desligado quebra a rede unificada.",
        "Lê SSID.1/2.Enable e SSID.1/2.SSID via datamodel.",
        f"SSID.{u}.Enable == 0 E SSID.{ou}.Enable == 1 E nomes iguais",
        f"Ativa SSID.{u} e AccessPoint.{u} e recarrega o Wi-Fi.")
    f[f"wifi_iface_{'24' if b == '24' else '5'}ghz_status"] = ("WIFI", f"Interface WLAN {band} ({iface}) Não Carregada",
        f"A interface física {iface} não existe apesar de Rádio e SSID estarem ativos.",
        f"Procura {iface} em ifconfig e lê SSID.{u}.Enable e Radio.{u}.Enable.",
        f"{iface} ausente E SSID.{u} == 1 E Radio.{u} == 1",
        f"Reaplica SSID.{u}, AccessPoint.{u} e Radio.{u} = 1 e recarrega o Wi-Fi.")
f["wifi_out_mem"] = ("WIFI", "Driver Wi-Fi Sem Memória",
    "O driver Wi-Fi reportou falhas de alocação de memória.",
    "Lê o contador /tmp/WIFI_OUT_MEM.",
    "Contador > 0", "Sem healing live — escala diretamente para reboot.")

# ---------------- Askey TCG310J
f = D["tcg310j"] = {}
f["dnsmasq"] = ("NETWORK", "Processo dnsmasq em Estado Zombie",
    "Um dnsmasq zombie deixa os clientes sem DNS/DHCP.",
    "Procura processos dnsmasq em estado Z em top.",
    "Pelo menos um dnsmasq zombie",
    "Mata o dnsmasq e relança-o com /var/dnsmasq.conf.")
f["bzip2_cpu_load"] = ("SYSTEM", "Carga de CPU Elevada",
    "Monitoriza a carga média do CPU normalizada pelo número de cores.",
    "Calcula (loadavg 1 min / n.º CPUs) × 100 / 2 a partir de /proc/loadavg e /proc/cpuinfo.",
    "Carga calculada ≥ 60", "Sem ação corretiva — apenas monitorização e reporte.")
f["digit_map"] = ("VOICE", "Digit Map de Voz Ausente",
    "Sem digit map o MTA não consegue encaminhar corretamente as chamadas.",
    "Lê o digit map via SNMP no MTA e o BootFileName do cable modem.",
    "Digit map vazio E BootFileName == '*VN*'",
    "Sem healing live — escala diretamente para reboot.")
f["syscfg_check"] = ("STORAGE", "Corrupção da Base syscfg.db (NVRAM)",
    "Linhas malformadas na syscfg.db podem corromper a configuração persistente.",
    "Conta linhas com vários '=' ou sem '=' em /nvram/syscfg.db.",
    "Pelo menos uma linha malformada",
    "Sem healing live — escala diretamente para factory reset.")
for b, u, iface in (("24", "1", "wlan0"), ("5", "2", "wlan1")):
    band = "2.4 GHz" if b == "24" else "5 GHz"
    f[f"wifi_radio_{b}_enable"] = ("WIFI", f"Rádio {band} vs Modo EcoWiFi",
        f"O rádio {band} deve estar ligado, exceto quando o EcoWiFi está ativo.",
        f"Lê Radio.{u}.Enable e X_NOS_PT_EcoWifi.Active via dmcli.",
        "Rádio e EcoWiFi.Active com o mesmo valor (ambos false ou ambos true)",
        f"Ambos false: liga Radio.{u} + ApplySetting. Ambos true: desativa o EcoWiFi.")
    f[f"wifi_radio_{b}_status"] = ("WIFI", f"Estado do Rádio {band} Incoerente",
        f"O estado operacional do rádio {band} não corresponde ao EcoWiFi nem ao SSID.",
        f"Lê Radio.{u}.Status, EcoWifi.Active e SSID.{u}.Enable via dmcli.",
        "Não é (Up sem EcoWiFi) nem (Down com EcoWiFi) nem (Down com SSID desativado)",
        "Sem healing live — escala diretamente para reboot.")
    f[f"wifi_inteface_wlan_{b}_load"] = ("WIFI", f"Interface WLAN {band} ({iface}) Não Carregada",
        f"A interface física {iface} desapareceu do kernel apesar de Rádio e SSID estarem ativos.",
        f"Procura {iface} em ifconfig e lê Radio.{u}.Enable e SSID.{u}.Enable.",
        f"{iface} ausente E Radio.{u} == true E SSID.{u} == true",
        f"Reaplica SSID.{u} e Radio.{u} = true + ApplySetting.")
    f[f"wifi_ssid_{b}_status"] = ("WIFI", f"SSID {band} em Erro",
        f"O SSID {band} reporta estado Error.",
        f"Lê Device.WiFi.SSID.{u}.Status via dmcli.",
        f"SSID.{u}.Status == Error", "Sem healing live — escala diretamente para reboot.")
    f[f"wifi_wlan_{b}_temperature"] = ("WIFI", f"Temperatura do Chip Wi-Fi {band}",
        f"Sobreaquecimento do chip {band} causa quebras e degradação do Wi-Fi.",
        f"Lê a temperatura com iw {iface}_0 cecli temperature2.",
        "Temperatura ≥ 95 ºC (valor não numérico = null)",
        "Sem healing live — escala diretamente para reboot.")
for key, tag, title, esc in (("needs_agent_restart", "NEEDS_AGENT_RESTART", "Agente Wi-Fi Precisa de Restart", "reboot"),
                             ("needs_reboot", "NEEDS_REBOOT", "Wi-Fi Precisa de Reboot", "reboot"),
                             ("unfixable", "UNFIXABLE", "Falha Wi-Fi Irrecuperável", None)):
    f[f"wifi_heal_{key}"] = ("WIFI", f"Self-Heal Wi-Fi: {title}",
        f"O self-heal interno do firmware sinalizou {tag} num dos rádios.",
        "Lê X_NOS_PT_SelfHeal.WiFi.{1,2}.HealthStatus.1.Name via dmcli.",
        f"HealthStatus contém {tag}",
        f"Sem healing live — escala diretamente para {esc}." if esc else
        "Sem ação de healing (sem reboot nem reset) — o CPE é sinalizado para troca de equipamento.")
for n in range(4):
    f[f"eth{n}_speed"] = eth(n, f"dmcli Ethernet.Interface.{n + 1}")
f["recover_voice_service"] = ("VOICE", "Linhas SIP Presas em Registo",
    "Ambas as linhas de voz ficam presas em Initializing/Registering sem serviço.",
    "Lê VoiceProfile.1.Line.1/2.SIP.Status via dmcli.",
    "Linhas 1 e 2 em Initializing ou Registering (nenhuma Up)",
    "Mata o CcspMtaAgentSsp (reinício do agente MTA) e aguarda 15 s.")
f["uptime_upper_15days"] = ("SYSTEM", "Uptime Superior a 15 Dias",
    "Reboot preventivo para evitar degradação acumulada (memória, tabelas, etc.).",
    "Lê Device.DeviceInfo.UpTime via dmcli.",
    "UpTime > 1 296 000 s (15 dias)", "Sem healing live — escala diretamente para reboot.")
f["enable_ecowifi"] = ("WIFI", "Ambos os SSIDs Desligados",
    "Evita que o cliente fique sem qualquer rede Wi-Fi.",
    "Lê SSID.1.Enable e SSID.2.Enable via dmcli.",
    "SSID.1 == false E SSID.2 == false",
    "Ativa o EcoWiFi e liga os SSIDs 1 e 2.")
f["nfq_handler_process_check"] = ("SYSTEM", "Patch do misc_handler (bloco ut_plat)",
    "Garante 'exit 0' após a linha ut_plat em misc_handler.sh para impedir o arranque do handler NFQ.",
    "Verifica se existe 'exit 0' na linha seguinte a ut_plat em /etc/utopia/service.d/misc_handler.sh.",
    "'exit 0' em falta", "Insere 'exit 0' após ut_plat via sed.")
f["block_local_page_php"] = ("SECURITY", "Bloqueio da Página Local (80/443)",
    "Impede o acesso à interface web local a partir da LAN (br+) e de l2sd0.106.",
    "Valida a cadeia NOS_LOCALPAGE (DROP nas portas 80/443) em iptables e ip6tables, na 1.ª posição do INPUT.",
    "Cadeia ausente, incompleta ou fora da 1.ª posição do INPUT",
    "Recria NOS_LOCALPAGE com as regras DROP e reinsere-a no topo do INPUT.")

ESC = {
    "reboot": "Reboot do CPE se a regra continuar NOK.",
    "factory-reset": "Factory Reset se a regra continuar NOK.",
    "none": "Nenhum — correção live sem reboot.",
}
# Manifest escalation values outside the dashboard schema (reboot | factory-reset | none),
# mapped to an allowed `reboot` value plus a specific escalation text.
ESC_MAP = {
    "change-device": ("none", "Nenhum — sem reboot nem reset; o CPE é sinalizado para troca de equipamento."),
}

# ---------------------------------------------------------------- build
meta_js, db_js = [], []
for key, path, sep, name, short, tech_short, tech in MODELS:
    with io.open(path, encoding="utf-8") as fh:
        raw = [l.rstrip("\r\n") for l in fh if l.strip()]
    meta, rules = {}, []
    for line in raw:
        parts = line.split(sep)
        if parts[0].startswith("manifest_"):
            meta[parts[0]] = parts[1].strip()
            continue
        rname, check = parts[0].strip(), parts[1]
        heal = parts[2] if len(parts) > 2 else ""
        tail = [p.strip() for p in parts[3:] if p.strip()]
        raw_esc = tail[0] if tail else "none"
        reboot, escalation = ESC_MAP.get(raw_esc, (raw_esc, ESC.get(raw_esc)))
        if reboot not in ESC:
            raise SystemExit(f"Unsupported escalation '{raw_esc}' for {key}/{rname}")
        if rname not in D[key]:
            raise SystemExit(f"Missing description for {key}/{rname}")
        cat, title, summary, detect, trigger, action = D[key][rname]
        if not heal.strip() and reboot == "none" and "Sem ação" not in action:
            raise SystemExit(f"Inconsistent action for {key}/{rname}")
        rules.append({
            "id": f"{key}_{rname}", "name": rname, "category": cat, "title": title,
            "summary": summary, "detect": detect, "trigger": trigger, "action": action,
            "escalation": escalation, "reboot": reboot,
            "checkFormatted": fmt_bash(check),
            "healFormatted": fmt_bash(heal) or "# Sem script de healing — apenas verificação"
                             + (" (escalamento direto)" if raw_esc != "none" else ""),
        })
    missing = set(D[key]) - {r["name"] for r in rules}
    if missing:
        raise SystemExit(f"Unused descriptions {key}: {missing}")
    cats = ["ALL"] + [c for c in CAT_ORDER if any(r["category"] == c for r in rules)]
    m = {"name": name, "shortName": short, "techShort": tech_short,
         "manifest": meta["manifest_name"], "version": "v" + meta["manifest_version"],
         "technology": tech, "categories": cats}
    meta_js.append(f"      {key}: " + json.dumps(m, ensure_ascii=False, indent=2).replace("\n", "\n      "))
    body = ",\n".join("        " + json.dumps(r, ensure_ascii=False, indent=2).replace("\n", "\n        ") for r in rules)
    db_js.append(f"      {key}: [\n{body}\n      ]")
    print(key, len(rules), "rules", cats)

import os

M0 = "    const modelsMeta = {\n"
M1 = "\n    };\n\n    const database = {\n"
D1 = "\n    };\n\n    let activeModel"


def split_blocks(h):
    i0 = h.index(M0) + len(M0)
    i1 = h.index(M1, i0)
    i2 = h.index(D1, i1)
    return h[:i0], h[i0:i1], h[i1 + len(M1):i2], h[i2:]


# ---------------------------------------------------------------- full manifest lines
# Raw manifest line per dashboard rule (check / heal / escalation fields), shown in the
# "Comando completo" section. Hub 5 and FAST 5657 group several manifest lines per rule.
MANIFEST_SRC = {
    "hub5": (BASE + r"\hitron v5\261110_check_cpe_health_chita_hub5.txt", "@"),
    "fast5657": (BASE + r"\f5657\check_cpe_health_sagem_fast5657.txt", "\u20ac"),
}
for key, path, sep, *_ in MODELS:
    MANIFEST_SRC[key] = (path, sep)
# Hub 5 / FAST 5657 come from the original dashboard, where several manifest lines were
# grouped into one rule. Each group is split into one rule per manifest line (same order
# as the manifest), with band/port-specific texts.
BASE_MODELS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "base_models.json")
PREFIX = {"hub5": "", "fast5657": "f5657_"}


def _band(b):
    return "2.4 GHz" if b == "24" else "5 GHz"


SPLIT = {"hub5": {}, "fast5657": {}}
SPLIT["hub5"]["wifi_ssid_advertisement"] = {
    f"wifi_ssid_{k}_advertisement_enable": dict(
        title=f"Broadcast do {lbl}",
        summary=f"Impede que o {lbl} (AccessPoint {ap}) fique oculto aos dispositivos clientes.",
        detect=f"Lê Device.WiFi.AccessPoint.{ap}.SSIDAdvertisementEnabled via dmcli.",
        trigger=f"AccessPoint.{ap}.SSIDAdvertisementEnabled != true",
        action=f"Força AccessPoint.{ap}.SSIDAdvertisementEnabled a true via dmcli.")
    for k, ap, lbl in (("24", 1, "SSID Principal 2.4 GHz"), ("5", 2, "SSID Principal 5 GHz"),
                       ("guest24", 3, "SSID Guest 2.4 GHz"), ("guest5", 4, "SSID Guest 5 GHz"))}
SPLIT["hub5"]["wifi_pci_devices"] = {
    f"wifi_pci_device_{b}": dict(
        title=f"Controlador PCI Wi-Fi {_band(b)} (modo {m})",
        summary=f"Confirma que o controlador PCI da banda {_band(b)} (modo {m}) está presente no barramento.",
        detect=f"Procura o modo {m} nos ficheiros hwmodes em /sys/devices/pci0000:00.",
        trigger=f"Nenhum controlador com modo {m} encontrado")
    for b, m in (("24", "11B"), ("5", "11A"))}
SPLIT["hub5"]["wifi_inteface_wlan_load"] = {
    f"wifi_inteface_wlan_{b}_load": dict(
        title=f"Carregamento da Interface Linux {i} ({_band(b)})",
        summary=f"Recupera a ausência da interface {i} quando o rádio {_band(b)} está ativo.",
        detect=f"Conta '{i}' no ifconfig e lê Device.WiFi.Radio.{r}.Enable via dmcli.",
        trigger=f"Interface {i} inexistente (0) mas Radio.{r}.Enable == true")
    for b, i, r in (("24", "wifi0", 1), ("5", "wifi1", 2))}
SPLIT["hub5"]["wifi_ssid_status_error"] = {
    f"wifi_ssid_{b}_status": dict(
        title=f"Estado de Erro no SSID {_band(b)}",
        summary=f"Deteta crash interno no ponto de acesso do SSID {s} ({_band(b)}).",
        detect=f"Lê Device.WiFi.SSID.{s}.Status via dmcli.",
        trigger=f"SSID.{s}.Status == 'Error'")
    for b, s in (("24", 1), ("5", 2))}
SPLIT["hub5"]["hub5_eth_speed"] = {
    f"eth{n}_speed": dict(
        title=f"Degradação de Velocidade na Porta LAN eth{n}",
        summary=f"Regista o bitrate da porta eth{n} em /tmp/ETH{n}_Speed e sinaliza quedas de velocidade.",
        detect=f"Compara Device.Ethernet.Interface.{n + 1}.CurrentBitRate com /tmp/ETH{n}_Speed se a porta estiver Up.",
        trigger=f"Bitrate de eth{n} diminuiu com a porta Up")
    for n in range(4)}
SPLIT["fast5657"]["f5657_wifi_radio_enable"] = {
    f"wifi_radio_{b}_enable": dict(
        title=f"Sincronização Rádio vs SSID ({_band(b)})",
        summary=f"Deteta inconsistência entre o rádio {u} ({_band(b)}) desativado e o estado do SSID {u}.",
        detect=f"Compara Radio[@uid='{u}']/Enable e SSID[@uid='{u}']/Status via xmo-client.",
        trigger=f"Radio {u} == false e SSID {u} != LOWERLAYERDOWN",
        action=f"Se Radio {u} == false e SSID {u} == DOWN, reativa o nó SSID {u} via xmo-client.")
    for b, u in (("24", 1), ("5", 2))}
SPLIT["fast5657"]["f5657_wifi_radio_status"] = {
    f"wifi_radio_{b}_status": dict(
        title=f"Rádio {_band(b)} em Estado DOWN Anómalo",
        summary=f"Deteta o rádio {u} ({_band(b)}) em DOWN apesar de configurado como ativo no rádio e no SSID.",
        detect=f"Cruza Radio[@uid='{u}']/Status, Radio[@uid='{u}']/Enable e SSID[@uid='{u}']/Enable.",
        action=f"Reativa explicitamente o Radio {u} e o AccessPoint {u} via xmo-client.")
    for b, u in (("24", 1), ("5", 2))}
SPLIT["fast5657"]["f5657_wifi_ssid_status"] = {
    f"wifi_ssid_{b}_status": dict(
        title=f"SSID {_band(b)} Bloqueado ou em Dormant",
        summary=f"Corrige o SSID {u} ({_band(b)}) preso em DORMANT, LOWERLAYERDOWN ou DOWN.",
        detect=f"Lê SSID[@uid='{u}']/Status, SSID[@uid='{u}']/Enable e Radio[@uid='{u}']/Enable via xmo-client.",
        trigger=f"SSID {u} em DOWN, DORMANT ou LOWERLAYERDOWN com o rádio {u} ativo",
        action=f"Força a reinicialização do SSID {u} e do AccessPoint {u}.")
    for b, u in (("24", 1), ("5", 2))}
SPLIT["fast5657"]["f5657_wifi_inteface_wlan_load"] = {
    f"wifi_inteface_wlan_{b}_load": dict(
        title=f"Interface Kernel {i} ({_band(b)})",
        summary=f"Recupera a ausência da interface Broadcom '{i}' no ifconfig quando a banda {_band(b)} está ativa.",
        detect=f"Conta '{i}' no /sbin/ifconfig e lê Radio[@uid='{u}']/Enable e SSID[@uid='{u}']/Enable.",
        trigger=f"{i} ausente no ifconfig com Radio {u} e SSID {u} ativos",
        action=f"Executa /sbin/ifconfig {i} up ou reativa os nós {u} via xmo-client.")
    for b, i, u in (("24", "wl1", 1), ("5", "wl0", 2))}
SPLIT["fast5657"]["f5657_eth_speed"] = {
    f"eth{n}_speed": dict(
        title=f"Velocidade Ethernet na Porta eth{n}",
        summary=f"Lê /sys/devices/virtual/net/eth{n}/speed e deteta desnegociação na porta eth{n}.",
        detect=f"Compara a velocidade atual de eth{n} com /tmp/ETH{n}_Speed.",
        trigger=f"Velocidade de eth{n} inferior ao último valor registado com a porta 'up'")
    for n in range(4)}
GROUPS = {}


def read_manifest(path, sep):
    out = {}
    with io.open(path, encoding="utf-8") as fh:
        for line in (l.rstrip("\r\n") for l in fh):
            if line.strip() and not line.startswith("manifest_"):
                parts = line.split(sep)
                out[parts[0].strip()] = parts
    return out


def expand_base_models():
    base = json.load(io.open(BASE_MODELS, encoding="utf-8"))["db"]
    blocks = []
    for key in ("hub5", "fast5657"):
        path, sep = MANIFEST_SRC[key]
        lines = read_manifest(path, sep)
        rules = []
        for r in base[key]:
            names = SPLIT[key].get(r["id"])
            if not names:
                rules.append(r)
                continue
            for name, ov in names.items():
                parts = lines[name]
                fields = [p.strip() for p in parts[3:] if p.strip()]
                rules.append(dict(r, **ov, id=PREFIX[key] + name, name=name,
                                  reboot=fields[0] if fields else "none",
                                  checkFormatted=fmt_bash(parts[1]),
                                  healFormatted=fmt_bash(parts[2] if len(parts) > 2 else "")
                                  or "# Sem script de healing — apenas verificação"))
        names = [r["name"] for r in rules]
        if sorted(names) != sorted(lines):
            raise SystemExit(f"{key}: dashboard {len(names)} vs manifest {len(lines)} rules: "
                             f"{set(lines) ^ set(names)}")
        order = list(lines)
        rules.sort(key=lambda r: order.index(r["name"]))
        body = ",\n".join("        " + json.dumps(r, ensure_ascii=False, indent=2).replace("\n", "\n        ")
                          for r in rules)
        blocks.append(f"      {key}: [\n{body}\n      ]")
        print(key, len(rules), "rules")
    return ",\n".join(blocks)


def rule_ids(js_db_block, key):
    """Rule ids of model `key`, in dashboard order, from a JS `database` block."""
    start = js_db_block.index(f"      {key}: [")
    end = js_db_block.find("\n      ]", start)
    return re.findall(r'(?m)^\s*"?id"?:\s*"([^"]+)"', js_db_block[start:end])


def manifest_lines(db_block):
    out = {}
    for key, (path, sep) in MANIFEST_SRC.items():
        entries = {}
        with io.open(path, encoding="utf-8") as fh:
            for line in (l.rstrip("\r\n") for l in fh):
                if not line.strip() or line.startswith("manifest_"):
                    continue
                parts = line.split(sep)
                fields = [p.strip() for p in parts[3:]]
                entries[parts[0].strip()] = {
                    "name": parts[0].strip(), "sep": sep,
                    "check": fmt_bash(parts[1]), "heal": fmt_bash(parts[2] if len(parts) > 2 else ""),
                    "escFields": fields, "esc": next((f for f in fields if f), ""), "raw": line,
                }
        groups, used, out[key] = GROUPS.get(key, {}), set(), {}
        for rid in rule_ids(db_block, key):
            names = groups.get(rid) or [rid[len(key) + 1:] if rid.startswith(key + "_") else
                                        rid[len("f5657_"):] if rid.startswith("f5657_") else rid]
            missing = [n for n in names if n not in entries]
            if missing:
                raise SystemExit(f"Manifest lines not found for {key}/{rid}: {missing}")
            out[key][rid] = [entries[n] for n in names]
            used.update(names)
        if set(entries) - used:
            raise SystemExit(f"Manifest lines without dashboard rule in {key}: {set(entries) - used}")
    return out


# Original models (Hub 5, FAST 5657) come from base_models.json; UI/template comes from
# index.html so manual UI changes are preserved on regeneration.
base_meta = ",\n".join(
    f"      {k}: " + json.dumps(m, ensure_ascii=False, indent=2).replace("\n", "\n      ")
    for k, m in json.load(io.open(BASE_MODELS, encoding="utf-8"))["meta"].items())
tmpl = io.open(MAIN, encoding="utf-8").read()
head, _, _, tail = split_blocks(tmpl)
db_block = expand_base_models() + ",\n" + ",\n".join(db_js)
html = (head + base_meta + ",\n" + ",\n".join(meta_js) + M1 + db_block + tail)
ML0, ML1 = "/*MANIFEST_LINES_START*/\n", "\n    /*MANIFEST_LINES_END*/"
ml_js = "    const manifestLines = " + json.dumps(manifest_lines(db_block), ensure_ascii=False,
                                                  separators=(",", ":")) + ";"
i0, i1 = html.index(ML0) + len(ML0), html.index(ML1)
html = html[:i0] + ml_js + html[i1:]
io.open(MAIN, "w", encoding="utf-8", newline="\n").write(html)
print("written", MAIN)
