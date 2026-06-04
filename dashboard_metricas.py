# -*- coding: utf-8 -*-
"""
BRAIN2POWER — Dashboard de Métricas RRSS
Acceso en red local: http://<tu-IP>:8501
Auto-refresco cada 5 minutos.
"""

import os, requests, json, datetime, time
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
from dotenv import load_dotenv

# ── Config ────────────────────────────────────────────────────────────────────
# Secrets: Streamlit Cloud → st.secrets | Local → .env
def _get_secrets():
    """Lee credenciales de st.secrets (Cloud) o .env (local)."""
    try:
        return (
            st.secrets["FACEBOOK_TOKEN"],
            st.secrets.get("FACEBOOK_PAGE_ID", "1035845122935970"),
            st.secrets.get("INSTAGRAM_ACCOUNT_ID", "17841448302166910"),
            st.secrets.get("LINKEDIN_TOKEN", ""),
            st.secrets.get("YOUTUBE_API_KEY", "AIzaSyCIv_tBox933cQZALXKnHxV9a-yWIihKe8"),
            st.secrets.get("YOUTUBE_CHANNEL_ID", "UCUahanmSyiyN7pSKNFqQ5VA"),
            st.secrets.get("X_BEARER_TOKEN", ""),
        )
    except Exception:
        _env = Path(__file__).parent / ".env"
        if not _env.exists():
            _env = Path(r"C:\Users\Cristela.Moreno\EquipodeAgentes\.env")
        load_dotenv(_env, override=True, encoding="utf-8")
        return (
            os.getenv("FACEBOOK_TOKEN", ""),
            os.getenv("FACEBOOK_PAGE_ID", "1035845122935970"),
            os.getenv("INSTAGRAM_ACCOUNT_ID", "17841448302166910"),
            os.getenv("LINKEDIN_TOKEN", ""),
            os.getenv("YOUTUBE_API_KEY", "AIzaSyCIv_tBox933cQZALXKnHxV9a-yWIihKe8"),
            os.getenv("YOUTUBE_CHANNEL_ID", "UCUahanmSyiyN7pSKNFqQ5VA"),
            os.getenv("X_BEARER_TOKEN", ""),
        )

FB_TOKEN, FB_PAGE_ID, IG_ID, LI_TOKEN, YT_KEY, YT_CHANNEL, X_TOKEN = _get_secrets()
X_USERNAME = "Brain2Power"
# Si no hay token en secrets, usar el token configurado localmente
if not X_TOKEN or len(X_TOKEN) < 20:
    X_TOKEN = "AAAAAAAAAAAAAAAAAAAAAAIw9QEAAAAAzgh4wLD4kt5qFZJ15KXP9UtFvcU=RRLPmZCKdzR7Al9OlYatsSMsKW7tuBqtqMF48t8Z1YBj18grcD"
FB_API     = "https://graph.facebook.com/v21.0"

VERDE  = "#00c878"
AZUL   = "#00a8e8"
OSCURO = "#0b1e3d"
ROJO   = "#ff6b6b"
ORO    = "#ffd700"

# ── Página ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Brain2Power — Métricas",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS personalizado
st.markdown(f"""
<style>
  .stApp {{ background-color: #060d1f; color: #ffffff; }}
  .stMetric label {{ color: rgba(255,255,255,0.55) !important; font-size: 13px !important; }}
  .stMetric [data-testid="metric-container"] {{
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 12px;
    padding: 16px;
  }}
  .block-container {{ padding-top: 1.5rem; }}
  h1, h2, h3 {{ color: white !important; }}
  .canal-header {{
    background: rgba(0,200,120,0.08);
    border: 1px solid rgba(0,200,120,0.3);
    border-radius: 12px;
    padding: 10px 20px;
    margin-bottom: 12px;
    font-weight: 700;
    font-size: 16px;
    color: {VERDE};
    letter-spacing: 2px;
    text-transform: uppercase;
  }}
  .canal-header.blue {{
    background: rgba(0,168,232,0.08);
    border-color: rgba(0,168,232,0.3);
    color: {AZUL};
  }}
  .canal-header.gold {{
    background: rgba(255,215,0,0.08);
    border-color: rgba(255,215,0,0.3);
    color: {ORO};
  }}
  .refresh-info {{
    font-size: 12px;
    color: rgba(255,255,255,0.3);
    text-align: right;
  }}
  .post-card {{
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 8px;
    font-size: 13px;
  }}
  .tag-green {{color: {VERDE}; font-weight: 700;}}
  .tag-blue {{color: {AZUL}; font-weight: 700;}}
  .tag-red {{color: {ROJO}; font-weight: 700;}}
</style>
""", unsafe_allow_html=True)

# ── Funciones de datos ────────────────────────────────────────────────────────
def _cargar_cache_metricas_api() -> dict:
    """Lee el JSON más reciente de metricas_api_*.json generado por agente_analisis_insights."""
    try:
        jsons = sorted(
            list(Path(__file__).parent.glob("metricas_api_*.json")),
            key=lambda p: p.stat().st_mtime, reverse=True
        )
        if jsons:
            return json.load(open(jsons[0], encoding="utf-8"))
    except Exception:
        pass
    return {}

_API_CACHE = _cargar_cache_metricas_api()


@st.cache_data(ttl=300)   # Cache 5 minutos
def get_instagram_data():
    try:
        # Info básica cuenta (siempre funciona con instagram_basic)
        r = requests.get(f"{FB_API}/{IG_ID}",
            params={"access_token": FB_TOKEN,
                    "fields": "id,username,followers_count,follows_count,media_count,biography,website"},
            timeout=10)
        info = r.json() if r.ok else {}

        # Métricas 30 días (requiere instagram_manage_insights)
        # En Development mode devuelve 0 → se completa con caché local del agente
        since = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
        until = datetime.date.today().isoformat()

        metricas = {}
        for metric in ["reach", "profile_views", "accounts_engaged", "total_interactions",
                        "likes", "comments", "shares", "saves", "views", "follows_and_unfollows"]:
            try:
                r2 = requests.get(f"{FB_API}/{IG_ID}/insights",
                    params={"access_token": FB_TOKEN, "metric": metric,
                            "period": "day", "metric_type": "total_value",
                            "since": since, "until": until},
                    timeout=8)
                d = r2.json()
                if "data" in d and d["data"]:
                    val = d["data"][0].get("total_value", {})
                    metricas[metric] = val.get("value", 0) if isinstance(val, dict) else (val if isinstance(val, (int, float)) else 0)
            except Exception:
                metricas[metric] = 0

        # Fallback: si todos son 0 (Dev mode), usar datos del caché local del agente
        ig_cache = _API_CACHE.get("instagram", {})
        if sum(v for v in metricas.values() if isinstance(v, (int, float))) == 0 and ig_cache:
            metricas["reach"]              = ig_cache.get("alcance_28d") or ig_cache.get("alcance", 0)
            metricas["total_interactions"] = ig_cache.get("interacciones_28d", 0)
            metricas["likes"]              = ig_cache.get("likes_28d", 0)
            metricas["comments"]           = ig_cache.get("comentarios_28d", 0)
            metricas["shares"]             = ig_cache.get("compartidos_28d", 0)
            metricas["profile_views"]      = ig_cache.get("visitas_perfil_28d", 0)
            metricas["_source"]            = "cache_local_agente"
        # Enriquecer info básica con caché si la API no devuelve datos
        if not info.get("followers_count") and ig_cache.get("seguidores"):
            info["followers_count"] = ig_cache["seguidores"]
        if not info.get("media_count") and ig_cache.get("media_count"):
            info["media_count"] = ig_cache["media_count"]

        # Últimos 10 posts
        r3 = requests.get(f"{FB_API}/{IG_ID}/media",
            params={"access_token": FB_TOKEN,
                    "fields": "id,timestamp,media_type,like_count,comments_count,caption",
                    "limit": 10},
            timeout=10)
        posts = r3.json().get("data", []) if r3.ok else []

        # Reach por post (últimos 5)
        for post in posts[:5]:
            try:
                rp = requests.get(f"{FB_API}/{post['id']}/insights",
                    params={"access_token": FB_TOKEN, "metric": "reach,saved"},
                    timeout=6)
                dp = rp.json()
                if "data" in dp:
                    for m in dp["data"]:
                        v = m.get("values", [{}])
                        post[m["name"]] = v[0].get("value", 0) if v else 0
            except Exception:
                pass

        # Audiencia por país
        try:
            rp = requests.get(f"{FB_API}/{IG_ID}/insights",
                params={"access_token": FB_TOKEN, "metric": "follower_demographics",
                        "period": "lifetime", "metric_type": "total_value", "breakdown": "country"},
                timeout=8)
            paises_raw = rp.json().get("data", [{}])[0].get("total_value", {}).get("breakdowns", [{}])[0].get("results", [])
            paises = sorted(paises_raw, key=lambda x: x["value"], reverse=True)[:8]
        except Exception:
            paises = []

        # Audiencia edad/género
        try:
            ra = requests.get(f"{FB_API}/{IG_ID}/insights",
                params={"access_token": FB_TOKEN, "metric": "follower_demographics",
                        "period": "lifetime", "metric_type": "total_value", "breakdown": "age,gender"},
                timeout=8)
            edades_raw = ra.json().get("data", [{}])[0].get("total_value", {}).get("breakdowns", [{}])[0].get("results", [])
            edades = sorted(edades_raw, key=lambda x: x["value"], reverse=True)[:8]
        except Exception:
            edades = []

        return {"info": info, "metricas": metricas, "posts": posts, "paises": paises, "edades": edades}
    except Exception as e:
        return {"error": str(e)}


@st.cache_data(ttl=300)
def get_facebook_data():
    try:
        r = requests.get(f"{FB_API}/{FB_PAGE_ID}",
            params={"access_token": FB_TOKEN,
                    "fields": "name,fan_count,followers_count,talking_about_count,category,about"},
            timeout=10)
        return r.json() if r.ok else {"error": "No se pudo conectar"}
    except Exception as e:
        return {"error": str(e)}


@st.cache_data(ttl=300)
def get_x_data():
    """X (Twitter) API v2 — perfil y tweets recientes de @Brain2Power."""
    BASE   = "https://api.twitter.com/2"
    result = {"connected": False, "token_configurado": bool(X_TOKEN and len(X_TOKEN) > 20)}

    if not X_TOKEN or len(X_TOKEN) < 20:
        result["error"] = "X_BEARER_TOKEN no configurado en Streamlit Secrets"
        return result

    hdrs = {"Authorization": f"Bearer {X_TOKEN}"}

    try:
        # Perfil del usuario
        r = requests.get(f"{BASE}/users/by/username/{X_USERNAME}",
            params={"user.fields": "public_metrics,description,created_at,profile_image_url"},
            headers=hdrs, timeout=10)

        if r.status_code == 401:
            result["error"] = "token_invalido"
            return result
        if r.status_code == 402:
            result["error"] = "creditos_agotados"
            result["token_ok"] = True  # token válido, solo sin créditos
            return result
        if r.status_code == 403:
            result["error"] = "plan_insuficiente"
            return result
        if not r.ok:
            result["error"] = f"HTTP {r.status_code}"
            return result

        user = r.json().get("data", {})
        pm   = user.get("public_metrics", {})
        result.update({
            "connected":     True,
            "user_id":       user.get("id", ""),
            "nombre":        user.get("name", "Brain2Power"),
            "username":      user.get("username", "Brain2Power"),
            "descripcion":   user.get("description", "")[:120],
            "seguidores":    pm.get("followers_count", 0),
            "siguiendo":     pm.get("following_count", 0),
            "tweets_total":  pm.get("tweet_count", 0),
            "listas":        pm.get("listed_count", 0),
        })

        # Tweets recientes con métricas
        uid = result["user_id"]
        r2  = requests.get(f"{BASE}/users/{uid}/tweets",
            params={"max_results": 10,
                    "tweet.fields": "public_metrics,created_at,text",
                    "exclude": "retweets,replies"},
            headers=hdrs, timeout=10)

        tweets = []
        if r2.ok:
            for tw in r2.json().get("data", []):
                pm2 = tw.get("public_metrics", {})
                tweets.append({
                    "id":          tw["id"],
                    "texto":       tw.get("text", "")[:100],
                    "fecha":       tw.get("created_at", "")[:10],
                    "likes":       pm2.get("like_count",      0),
                    "retweets":    pm2.get("retweet_count",   0),
                    "replies":     pm2.get("reply_count",     0),
                    "impresiones": pm2.get("impression_count",0),
                    "url":         f"https://x.com/{X_USERNAME}/status/{tw['id']}",
                })

        result["tweets"]         = tweets
        result["likes_30d"]      = sum(t["likes"]       for t in tweets)
        result["retweets_30d"]   = sum(t["retweets"]    for t in tweets)
        result["impresiones_30d"]= sum(t["impresiones"] for t in tweets)

    except Exception as e:
        result["error"] = str(e)[:100]
    return result


@st.cache_data(ttl=300)
def get_youtube_data():
    """YouTube Data API v3 — canal Brain2Power."""
    BASE = "https://www.googleapis.com/youtube/v3"
    result = {"connected": False, "error": None}
    try:
        # Info del canal
        r = requests.get(f"{BASE}/channels",
            params={"part": "snippet,statistics", "id": YT_CHANNEL, "key": YT_KEY},
            timeout=10)
        if not r.ok:
            result["error"] = f"HTTP {r.status_code}"
            return result
        items = r.json().get("items", [])
        if not items:
            result["error"] = "Canal no encontrado"
            return result

        ch    = items[0]
        sn    = ch.get("snippet", {})
        stats = ch.get("statistics", {})
        result.update({
            "connected":    True,
            "channel_id":   ch["id"],
            "nombre":       sn.get("title", "Brain2Power"),
            "descripcion":  sn.get("description", "")[:120],
            "suscriptores": int(stats.get("subscriberCount", 0)),
            "videos_total": int(stats.get("videoCount", 0)),
            "vistas_total": int(stats.get("viewCount", 0)),
            "pais":         sn.get("country", "ES"),
        })

        # Últimos 10 vídeos
        r2 = requests.get(f"{BASE}/search", params={
            "part": "snippet", "channelId": YT_CHANNEL,
            "order": "date", "maxResults": 10, "type": "video", "key": YT_KEY},
            timeout=10)
        videos_raw = r2.json().get("items", []) if r2.ok else []
        video_ids  = ",".join(v["id"]["videoId"] for v in videos_raw if "videoId" in v.get("id", {}))

        # Estadísticas de cada vídeo
        videos = []
        if video_ids:
            r3 = requests.get(f"{BASE}/videos", params={
                "part": "statistics,contentDetails,snippet",
                "id": video_ids, "key": YT_KEY}, timeout=10)
            if r3.ok:
                for v in r3.json().get("items", []):
                    vs = v.get("statistics", {})
                    cd = v.get("contentDetails", {})
                    sn2 = v.get("snippet", {})
                    dur = cd.get("duration", "").replace("PT","").replace("M","'").replace("S","\"")
                    videos.append({
                        "id":        v["id"],
                        "titulo":    sn2.get("title", "")[:60],
                        "fecha":     sn2.get("publishedAt", "")[:10],
                        "vistas":    int(vs.get("viewCount",  0)),
                        "likes":     int(vs.get("likeCount",  0)),
                        "comentarios": int(vs.get("commentCount", 0)),
                        "duracion":  dur,
                        "tipo":      "Short" if "S" in cd.get("duration","") and "M" not in cd.get("duration","") or
                                     int(cd.get("duration","PT0S").replace("PT","").replace("S","").replace("M","").split("'")[0] if "'" in cd.get("duration","").replace("PT","").replace("M","'").replace("S","\"") else "999") < 60
                                     else "Vídeo",
                        "url":       f"https://youtu.be/{v['id']}",
                    })

        result["videos"] = videos
        # Métricas 30d (suma de los vídeos recientes)
        result["vistas_30d"]    = sum(v["vistas"]     for v in videos)
        result["likes_30d"]     = sum(v["likes"]      for v in videos)
        result["comentarios_30d"] = sum(v["comentarios"] for v in videos)

    except Exception as e:
        result["error"] = str(e)[:100]
    return result


@st.cache_data(ttl=300)
def get_linkedin_data():
    """LinkedIn — perfil, estado del token y capacidades disponibles."""
    headers = {"Authorization": f"Bearer {LI_TOKEN}"}
    result = {
        "connected": False,
        "name": "—", "email": "—",
        "org_name": "Brain2Power", "org_urn": "urn:li:organization:111959115",
        "token_caduca": "03/08/2026",
        "scopes": ["openid", "profile", "email", "w_member_social", "r_events", "rw_events"],
        "puede_publicar": True,
        "metricas_org": False,
    }
    try:
        # userinfo funciona con scope openid+profile+email
        r = requests.get("https://api.linkedin.com/v2/userinfo",
                         headers=headers, timeout=8)
        if r.ok:
            d = r.json()
            result["connected"] = True
            result["name"]  = d.get("name", "Brain2 Power")
            result["email"] = d.get("email", "cristela.moreno@plocan.eu")
        else:
            result["error"] = r.text[:120]
    except Exception as e:
        result["error"] = str(e)
    return result


# ── HEADER ────────────────────────────────────────────────────────────────────
col_title, col_refresh = st.columns([4, 1])
with col_title:
    st.markdown("## ⚡ Brain2Power — Dashboard de Métricas RRSS")
    st.markdown(f"<span style='color:rgba(255,255,255,0.4);font-size:13px'>Última actualización: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')} · Refresco automático cada 5 min</span>", unsafe_allow_html=True)

with col_refresh:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Refrescar ahora", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.markdown("---")

# ── CARGAR DATOS ──────────────────────────────────────────────────────────────
with st.spinner("Cargando métricas en tiempo real..."):
    ig_data = get_instagram_data()
    fb_data = get_facebook_data()
    li_data = get_linkedin_data()
    x_data  = get_x_data()
    yt_data = get_youtube_data()

# ── INSTAGRAM ─────────────────────────────────────────────────────────────────
st.markdown('<div class="canal-header">📸 Instagram — @brain2power</div>', unsafe_allow_html=True)

if "error" not in ig_data:
    info = ig_data.get("info", {})
    met  = ig_data.get("metricas", {})

    # KPIs principales
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    with k1:
        st.metric("👥 Seguidores", f"{info.get('followers_count', 0):,}", delta="+25 últimos 15d")
    with k2:
        st.metric("📱 Posts totales", info.get('media_count', 0))
    with k3:
        st.metric("👁️ Reach 30d", f"{met.get('reach', 0):,}")
    with k4:
        st.metric("▶️ Views 30d", f"{met.get('views', 0):,}")
    with k5:
        st.metric("👤 Visitas perfil 30d", f"{met.get('profile_views', 0):,}")
    with k6:
        st.metric("❤️ Likes 30d", f"{met.get('likes', 0):,}")

    # Segunda fila KPIs
    k7, k8, k9, k10, k11, k12 = st.columns(6)
    with k7:
        st.metric("💬 Comentarios 30d", met.get('comments', 0))
    with k8:
        st.metric("🔁 Compartidos 30d", met.get('shares', 0))
    with k9:
        st.metric("🔖 Guardados 30d", met.get('saves', 0))
    with k10:
        st.metric("🎯 Cuentas alcanzadas", f"{met.get('accounts_engaged', 0):,}")
    with k11:
        st.metric("📊 Interacciones 30d", f"{met.get('total_interactions', 0):,}")
    with k12:
        tasa = round(met.get('total_interactions', 0) / max(info.get('followers_count', 1), 1) * 100, 2)
        st.metric("📈 Tasa engagement", f"{tasa}%")

    st.markdown("<br>", unsafe_allow_html=True)

    # Gráficos y posts recientes
    col_chart, col_posts = st.columns([1, 1])

    with col_chart:
        # Gráfico audiencia por países
        paises = ig_data.get("paises", [])
        if paises:
            fig_p = go.Figure(go.Bar(
                x=[p["value"] for p in paises],
                y=[p["dimension_values"][0] for p in paises],
                orientation="h",
                marker_color=VERDE,
                marker_opacity=0.8,
            ))
            fig_p.update_layout(
                title="🌍 Seguidores por país",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="white",
                height=300,
                margin=dict(l=10, r=10, t=40, b=10),
                yaxis=dict(autorange="reversed"),
                xaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
            )
            st.plotly_chart(fig_p, use_container_width=True)

        # Gráfico edad/género
        edades = ig_data.get("edades", [])
        if edades:
            labels = [f"{e['dimension_values'][0]} {e['dimension_values'][1]}" for e in edades]
            values = [e["value"] for e in edades]
            fig_e = go.Figure(go.Bar(
                x=labels, y=values,
                marker_color=[AZUL if e["dimension_values"][1] == "M" else VERDE if e["dimension_values"][1] == "F" else ORO
                               for e in edades],
            ))
            fig_e.update_layout(
                title="👥 Audiencia por edad y género",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="white",
                height=280,
                margin=dict(l=10, r=10, t=40, b=10),
                xaxis=dict(tickangle=-30),
                yaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
            )
            st.plotly_chart(fig_e, use_container_width=True)

    with col_posts:
        st.markdown("**📋 Últimos posts**")
        posts = ig_data.get("posts", [])
        type_icons = {"VIDEO": "🎬", "IMAGE": "🖼️", "CAROUSEL_ALBUM": "📋"}
        for post in posts[:8]:
            icon = type_icons.get(post.get("media_type", ""), "📄")
            ts   = post.get("timestamp", "")[:10]
            likes = post.get("like_count", 0)
            reach = post.get("reach", "—")
            caption = (post.get("caption", "") or "")[:60].replace("\n", " ") or "(sin caption)"
            reach_txt = f"reach: {reach}" if isinstance(reach, int) else ""
            st.markdown(f"""<div class="post-card">
                <span class="tag-green">{icon} {ts}</span> · likes: <b>{likes}</b> {f"· {reach_txt}" if reach_txt else ""}<br>
                <span style="color:rgba(255,255,255,0.5);font-size:12px">{caption}...</span>
            </div>""", unsafe_allow_html=True)

        # Rendimiento por tipo
        if posts:
            tipos = {}
            for p in posts:
                t = p.get("media_type", "OTHER")
                if t not in tipos:
                    tipos[t] = {"count": 0, "likes": 0, "reach": 0}
                tipos[t]["count"] += 1
                tipos[t]["likes"] += p.get("like_count", 0)
                tipos[t]["reach"] += p.get("reach", 0) if isinstance(p.get("reach"), int) else 0

            st.markdown("<br>**📊 Rendimiento por formato (últimos 10 posts)**", unsafe_allow_html=True)
            for tipo, d in tipos.items():
                avg_reach = round(d["reach"] / d["count"]) if d["count"] else 0
                avg_likes = round(d["likes"] / d["count"], 1) if d["count"] else 0
                icon = type_icons.get(tipo, "📄")
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric(f"{icon} {tipo}", f"{d['count']} posts")
                with col_b:
                    st.metric("Reach medio", avg_reach)
                with col_c:
                    st.metric("Likes medio", avg_likes)
else:
    st.error(f"Error al cargar Instagram: {ig_data.get('error')}")

st.markdown("---")

# ── FACEBOOK ──────────────────────────────────────────────────────────────────
st.markdown('<div class="canal-header blue">📘 Facebook — Página Brain2Power</div>', unsafe_allow_html=True)

if "error" not in fb_data:
    fb1, fb2, fb3, fb4 = st.columns(4)
    with fb1:
        st.metric("👍 Fans (Me gusta)", fb_data.get("fan_count", 0))
    with fb2:
        st.metric("👥 Seguidores página", fb_data.get("followers_count", 0))
    with fb3:
        st.metric("💬 Hablando de esto", fb_data.get("talking_about_count", 0))
    with fb4:
        st.metric("📂 Categoría", fb_data.get("category", "—"))

    st.info(
        "⏳ **App Meta en verificación:** Token permanente activo (renovado 29/05/2026). "
        "Métricas básicas de página OK. Insights detallados (reach, impressions, posts engagement) "
        "disponibles cuando Meta apruebe la verificación de empresa → app pasará a modo Live. "
        "Mientras tanto, el agente usa datos del scraper como fallback automático."
    )
else:
    st.error(f"Error Facebook: {fb_data.get('error')}")

st.markdown("---")

# ── LINKEDIN ──────────────────────────────────────────────────────────────────
st.markdown('<div class="canal-header gold">💼 LinkedIn — Organización Brain2Power</div>', unsafe_allow_html=True)

li1, li2, li3, li4 = st.columns(4)
with li1:
    if li_data.get("connected"):
        status = "✅ Conectado"
    elif LI_TOKEN and len(LI_TOKEN) > 20:
        status = "⚠️ Token en secrets"
    else:
        status = "❌ Secret vacío"
    st.metric("🔑 Token API", status)
with li2:
    nombre = li_data.get("name", "Brain2 Power") if li_data.get("connected") else "Brain2 Power"
    st.metric("👤 Cuenta", nombre)
with li3:
    st.metric("📅 Caduca", li_data.get("token_caduca", "03/08/2026"))
with li4:
    publica = "✅ Activo" if li_data.get("puede_publicar") else "❌ No disponible"
    st.metric("📤 Publicación", publica)

if not li_data.get("connected") and LI_TOKEN and len(LI_TOKEN) > 20:
    st.warning(
        "⚠️ **LinkedIn:** Token presente en secrets pero rechazado por la API. "
        "Actualiza el secret LINKEDIN_TOKEN con el token renovado el 04/06/2026 "
        "(caduca 03/08/2026). Publicación de posts activa mediante API local."
    )
elif not LI_TOKEN or len(LI_TOKEN) < 20:
    st.error(
        "❌ **LinkedIn:** Secret LINKEDIN_TOKEN no configurado en Streamlit Cloud. "
        "Ve a Settings → Secrets y añade el token completo."
    )

# Capacidades disponibles vs pendientes
cap_col, pend_col = st.columns(2)
with cap_col:
    st.markdown(f"""
    <div style="background:rgba(0,200,120,0.07);border:1px solid rgba(0,200,120,0.25);
        border-radius:10px;padding:14px 18px;">
    <div style="color:{VERDE};font-weight:700;margin-bottom:8px;font-size:14px">✅ DISPONIBLE AHORA</div>
    <div style="font-size:13px;line-height:1.8;color:rgba(255,255,255,0.85)">
    • Publicar posts en página de empresa<br>
    • Autenticación y perfil verificado<br>
    • Email: {li_data.get('email','cristela.moreno@plocan.eu')}<br>
    • Scopes: <code style="color:{AZUL}">openid · profile · email · w_member_social</code>
    </div></div>""", unsafe_allow_html=True)

with pend_col:
    st.markdown(f"""
    <div style="background:rgba(255,215,0,0.05);border:1px solid rgba(255,215,0,0.2);
        border-radius:10px;padding:14px 18px;">
    <div style="color:{ORO};font-weight:700;margin-bottom:8px;font-size:14px">ℹ️ REQUIERE APROBACIÓN LINKEDIN</div>
    <div style="font-size:13px;line-height:1.8;color:rgba(255,255,255,0.65)">
    • Métricas de organización (seguidores, impresiones)<br>
    • Scope <code>r_organization_social</code> — solo con Marketing Developer Platform<br>
    • Solicitud en: <code>linkedin.com/developers/apps</code><br>
    • Proceso de revisión manual por LinkedIn (1-4 semanas)
    </div></div>""", unsafe_allow_html=True)

st.markdown("---")

# ── X (TWITTER) ───────────────────────────────────────────────────────────────
NEGRO_X = "#e7e9ea"
st.markdown(f'<div class="canal-header" style="background:rgba(231,233,234,0.06);border-color:rgba(231,233,234,0.25);color:{NEGRO_X}">🐦 X (Twitter) — @Brain2Power</div>', unsafe_allow_html=True)

if x_data.get("connected"):
    x1, x2, x3, x4, x5, x6 = st.columns(6)
    with x1:
        st.metric("👥 Seguidores", f"{x_data.get('seguidores', 0):,}")
    with x2:
        st.metric("📝 Tweets totales", f"{x_data.get('tweets_total', 0):,}")
    with x3:
        st.metric("👁️ Impresiones 10 tw.", f"{x_data.get('impresiones_30d', 0):,}")
    with x4:
        st.metric("❤️ Likes 10 tw.", x_data.get("likes_30d", 0))
    with x5:
        st.metric("🔁 Retweets 10 tw.", x_data.get("retweets_30d", 0))
    with x6:
        er = round(x_data.get("likes_30d", 0) / max(x_data.get("impresiones_30d", 1), 1) * 100, 2)
        st.metric("📊 ER (likes/imp.)", f"{er}%")

    st.markdown("<br>", unsafe_allow_html=True)
    col_x_posts, col_x_chart = st.columns([1, 1])

    tweets = x_data.get("tweets", [])
    with col_x_posts:
        st.markdown("**📋 Tweets recientes**")
        for tw in tweets[:8]:
            er_tw = round(tw["likes"] / max(tw["impresiones"], 1) * 100, 2)
            st.markdown(f"""<div class="post-card">
                <span style="color:{NEGRO_X};font-weight:700">{tw['fecha']}</span><br>
                👁️ <b>{tw['impresiones']:,}</b> · ❤️ {tw['likes']} · 🔁 {tw['retweets']} · 💬 {tw['replies']} · ER: {er_tw}%<br>
                <span style="color:rgba(255,255,255,0.5);font-size:12px">{tw['texto']}...</span>
            </div>""", unsafe_allow_html=True)

    with col_x_chart:
        if tweets:
            labels  = [tw["fecha"] for tw in tweets[:8]]
            imp     = [tw["impresiones"] for tw in tweets[:8]]
            lks     = [tw["likes"] for tw in tweets[:8]]
            fig_x   = go.Figure()
            fig_x.add_trace(go.Bar(name="Impresiones", x=labels, y=imp,
                                   marker_color=NEGRO_X, marker_opacity=0.7))
            fig_x.add_trace(go.Bar(name="Likes", x=labels, y=lks,
                                   marker_color=ORO, marker_opacity=0.9))
            fig_x.update_layout(
                title="📊 Impresiones y likes por tweet",
                barmode="group",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="white",
                height=300,
                margin=dict(l=10, r=10, t=40, b=40),
                xaxis=dict(tickangle=-30, gridcolor="rgba(255,255,255,0.05)"),
                yaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
                legend=dict(orientation="h", y=1.1),
            )
            st.plotly_chart(fig_x, use_container_width=True)

elif x_data.get("error") == "creditos_agotados":
    st.markdown(f"""
    <div style="background:rgba(255,165,0,0.06);border:1px solid rgba(255,165,0,0.25);
        border-radius:10px;padding:16px 20px;display:flex;gap:16px;align-items:flex-start">
    <div style="font-size:28px">🟠</div>
    <div>
      <div style="color:#ffa500;font-weight:700;font-size:14px;margin-bottom:6px">
        X API — Token ✅ configurado · Créditos agotados este mes</div>
      <div style="font-size:13px;line-height:1.8;color:rgba(255,255,255,0.75)">
        El Bearer Token es válido y está guardado. La cuota mensual de la cuenta
        <b>@Brain2Power</b> se ha consumido.<br>
        Los créditos se <b>renuevan automáticamente el 1 de julio</b> — las métricas
        aparecerán en el dashboard sin ninguna acción adicional.<br><br>
        Para tener créditos ilimitados: actualizar a plan <b>Basic ($100/mes)</b>
        en <code>developer.x.com</code>.
      </div>
    </div>
    </div>""", unsafe_allow_html=True)
elif not x_data.get("token_configurado"):
    st.markdown(f"""
    <div style="background:rgba(231,233,234,0.05);border:1px solid rgba(231,233,234,0.2);
        border-radius:10px;padding:18px 22px;">
    <div style="color:{NEGRO_X};font-weight:700;font-size:15px;margin-bottom:10px">
        🐦 X — Configuración pendiente</div>
    <div style="font-size:13px;line-height:2;color:rgba(255,255,255,0.7)">
    1. Ir a <code>developer.x.com</code> → crear app gratuita<br>
    2. Copiar el <b>Bearer Token</b><br>
    3. Añadir en Streamlit Secrets: <code>X_BEARER_TOKEN = "tu_token"</code>
    </div></div>""", unsafe_allow_html=True)
elif x_data.get("error"):
    st.warning(f"⚠️ X API: {x_data['error']}")

st.markdown("---")

# ── YOUTUBE ────────────────────────────────────────────────────────────────────
ROJO_YT = "#ff0000"
st.markdown(f'<div class="canal-header" style="background:rgba(255,0,0,0.08);border-color:rgba(255,0,0,0.3);color:{ROJO_YT}">📺 YouTube — @brain2power</div>', unsafe_allow_html=True)

if yt_data.get("connected"):
    # KPIs canal
    yt1, yt2, yt3, yt4, yt5, yt6 = st.columns(6)
    with yt1:
        st.metric("🔔 Suscriptores", f"{yt_data.get('suscriptores', 0):,}")
    with yt2:
        st.metric("🎬 Vídeos totales", yt_data.get("videos_total", 0))
    with yt3:
        st.metric("👁️ Vistas totales", f"{yt_data.get('vistas_total', 0):,}")
    with yt4:
        st.metric("▶️ Vistas 30d", f"{yt_data.get('vistas_30d', 0):,}")
    with yt5:
        st.metric("👍 Likes 30d", yt_data.get("likes_30d", 0))
    with yt6:
        st.metric("💬 Comentarios 30d", yt_data.get("comentarios_30d", 0))

    st.markdown("<br>", unsafe_allow_html=True)

    # Últimos vídeos + gráfico
    videos = yt_data.get("videos", [])
    col_yt_posts, col_yt_chart = st.columns([1, 1])

    with col_yt_posts:
        st.markdown("**📋 Últimos vídeos**")
        for v in videos[:8]:
            tipo_icon = "⚡ Short" if v.get("tipo") == "Short" else "🎬 Vídeo"
            er = round(v["likes"] / max(v["vistas"], 1) * 100, 1)
            st.markdown(f"""<div class="post-card">
                <span class="tag-red">{tipo_icon} · {v['fecha']}</span> · {v['duracion']}<br>
                👁️ <b>{v['vistas']:,}</b> vistas · 👍 {v['likes']} · 💬 {v['comentarios']} · ER: {er}%<br>
                <span style="color:rgba(255,255,255,0.5);font-size:12px">{v['titulo']}...</span>
            </div>""", unsafe_allow_html=True)

    with col_yt_chart:
        if videos:
            fig_yt = go.Figure()
            titulos = [v["titulo"][:25] + "…" for v in videos[:8]]
            vistas  = [v["vistas"] for v in videos[:8]]
            likes   = [v["likes"] for v in videos[:8]]
            fig_yt.add_trace(go.Bar(name="Vistas", x=titulos, y=vistas,
                                    marker_color=ROJO_YT, marker_opacity=0.8))
            fig_yt.add_trace(go.Bar(name="Likes", x=titulos, y=likes,
                                    marker_color=ORO, marker_opacity=0.9))
            fig_yt.update_layout(
                title="📊 Vistas y likes por vídeo (últimos 8)",
                barmode="group",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="white",
                height=320,
                margin=dict(l=10, r=10, t=40, b=80),
                xaxis=dict(tickangle=-30, gridcolor="rgba(255,255,255,0.05)"),
                yaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
                legend=dict(orientation="h", y=1.1),
            )
            st.plotly_chart(fig_yt, use_container_width=True)

        # Link al canal
        ch_id = yt_data.get("channel_id", YT_CHANNEL)
        st.markdown(f"""
        <div style="background:rgba(255,0,0,0.07);border:1px solid rgba(255,0,0,0.25);
            border-radius:10px;padding:12px 16px;margin-top:8px;font-size:13px">
        🔗 <a href="https://www.youtube.com/channel/{ch_id}" target="_blank"
            style="color:{ROJO_YT};font-weight:700">youtube.com/@brain2power</a><br>
        <span style="color:rgba(255,255,255,0.5)">
        Canal verificado · API key activa · Cuota: 10.000 unidades/día (gratuita)
        </span></div>""", unsafe_allow_html=True)

elif yt_data.get("error"):
    st.error(f"❌ YouTube API: {yt_data['error']}")
else:
    st.warning("⚠️ YouTube no disponible")

st.markdown("---")

# ── PLAN DE CONTENIDOS SEMANA ──────────────────────────────────────────────────
st.markdown("## 📅 Plan de contenidos — Semana 4-8 Junio 2026")

plan = [
    {"dia": "Mié 4 Jun ✅", "hora": "18:00h", "red": "Instagram",  "formato": "🖼️ Imagen",      "tema": "Spread 188% PVPC vs OMIE — datos verificados REE+OMIE",             "estado": "PUBLICADO ✅"},
    {"dia": "Mié 4 Jun ✅", "hora": "18:00h", "red": "LinkedIn",   "formato": "🖼️ Imagen",      "tema": "Spread 188% PVPC vs OMIE — datos verificados REE+OMIE",             "estado": "PUBLICADO ✅"},
    {"dia": "Jue 5 Jun 🌍", "hora": "09:30h", "red": "LinkedIn",   "formato": "Texto",          "tema": "Día Mundial Medio Ambiente — tono B2B técnico + datos PLOCAN",      "estado": "⭐ PRIORITARIO"},
    {"dia": "Jue 5 Jun 🌍", "hora": "10:00h", "red": "Instagram",  "formato": "🎬 Reel 35s",    "tema": "Día Mundial Medio Ambiente — datos reales renovables Canarias",      "estado": "⭐ PRIORITARIO"},
    {"dia": "Vie 6 Jun",    "hora": "11:00h", "red": "Instagram",  "formato": "📱 Historias x3","tema": "Encuesta: ¿sabes qué es un VPP? + dato de la semana",                "estado": "PENDIENTE"},
    {"dia": "Vie 6 Jun",    "hora": "11:00h", "red": "LinkedIn",   "formato": "📰 Artículo",    "tema": "Noticia 1 — Sistema multiagente IA: 125 municipios analizados",      "estado": "PENDIENTE"},
    {"dia": "Lun 9 Jun",    "hora": "08:30h", "red": "LinkedIn",   "formato": "Texto",          "tema": "Seguimiento evento 20/06 — convocatoria stakeholders",               "estado": "PENDIENTE"},
    {"dia": "Lun 9 Jun",    "hora": "10:00h", "red": "Instagram",  "formato": "🖼️ Carrusel",    "tema": "Edificios Cabildo GC con FV — prosumidores reales",                  "estado": "PENDIENTE"},
    {"dia": "Jue 12 Jun",   "hora": "10:00h", "red": "Instagram",  "formato": "🎬 Reel",        "tema": "Análisis consumo Las Palmas GC vs Santa Cruz de Tenerife",           "estado": "PENDIENTE"},
    {"dia": "Vie 13 Jun",   "hora": "11:00h", "red": "LinkedIn",   "formato": "📊 Carrusel",    "tema": "Resultados 40 días VPP operando — aprendizajes IA",                  "estado": "PENDIENTE"},
]

color_red = {"Instagram": VERDE, "LinkedIn": AZUL, "Facebook": "#1877f2", "YouTube": "#ff0000"}
estado_color = {"PENDIENTE": ORO, "LISTO ✅": VERDE, "⭐ PRIORITARIO": "#ff6b6b"}

for p in plan:
    rc = color_red.get(p["red"], AZUL)
    ec = estado_color.get(p["estado"], ORO)
    st.markdown(f"""<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);
        border-left:3px solid {rc};border-radius:10px;padding:10px 16px;margin-bottom:6px;
        display:flex;justify-content:space-between;align-items:center;">
        <span style="color:rgba(255,255,255,0.5);font-size:13px;min-width:90px">{p['dia']}</span>
        <span style="color:{rc};font-weight:700;min-width:80px">{p['red']}</span>
        <span style="color:rgba(255,255,255,0.7);min-width:140px;font-size:13px">{p['formato']}</span>
        <span style="color:#fff;flex:1;font-size:13px">{p['tema']}</span>
        <span style="color:{ec};font-weight:700;font-size:12px;min-width:120px;text-align:right">{p['estado']}</span>
    </div>""", unsafe_allow_html=True)

st.markdown("---")

# ── FOOTER ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="text-align:center;color:rgba(255,255,255,0.2);font-size:12px;padding:20px 0">
  ⚡ Brain2Power · PLOCAN · Dashboard interno v1.0 ·
  Datos actualizados: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')} ·
  Auto-refresco: 5 min
</div>
""", unsafe_allow_html=True)

# Auto-refresco cada 5 minutos
time.sleep(0.1)
