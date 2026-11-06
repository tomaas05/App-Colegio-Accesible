# Demostración con HTTPS en la Wi-Fi del aula

Para las demos, un portátil del equipo sirve la aplicación y las tablets y móviles se conectan a la misma Wi-Fi (Propuesta Técnica, 5.2). Caddy pone HTTPS con un certificado local (RNF1.1.1). **Siempre con datos ficticios.**

## 1. Averigua la IP del portátil

- Ubuntu: `hostname -I`
- Windows: `ipconfig` (Adaptador de LAN inalámbrica → Dirección IPv4)

Supongamos `192.168.1.50`.

## 2. Ajusta `.env`

```text
DESPEGA_HOST=192.168.1.50
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.50
DJANGO_CSRF_TRUSTED_ORIGINS=https://192.168.1.50
```

## 3. Arranca con el perfil de demo

```bash
docker compose --profile demo up --build
```

La aplicación queda en `https://192.168.1.50`.

## 4. Instala el certificado raíz en los dispositivos

Sin este paso, los navegadores mostrarán un aviso de conexión no segura.

```bash
docker compose cp caddy:/data/caddy/pki/authorities/local/root.crt ./despega-root.crt
```

Pasa `despega-root.crt` a cada dispositivo e instálalo:

- **Android:** Ajustes → Seguridad → Cifrado y credenciales → Instalar un certificado → Certificado de CA.
- **iPhone / iPad:** ábrelo, Ajustes → Perfil descargado → Instalar; después Ajustes → General → Información → Ajustes de confianza de certificados → activar.
- **Windows:** doble clic → Instalar certificado → Equipo local → «Entidades de certificación raíz de confianza».
- **Ubuntu:** `sudo cp despega-root.crt /usr/local/share/ca-certificates/ && sudo update-ca-certificates`

No subas `despega-root.crt` al repositorio. Al acabar el proyecto, elimínalo de los dispositivos.

## 5. Cortafuegos

Si los dispositivos no llegan al portátil, permite los puertos 80 y 443:

- Ubuntu: `sudo ufw allow 80,443/tcp`
- Windows: acepta el aviso del Firewall de Windows para Docker Desktop en redes **privadas**.
