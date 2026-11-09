"""Visualização de perfis atmosféricos Skew-T para o ClimaCast.

Entrada: DataFrame de skewt_handler.get_vertical_profile_data, com colunas
pressure (hPa), temperature (°C), relative_humidity (%), u_component e
v_component (m/s). O primeiro nível deve representar a superfície.
"""

from datetime import date as Date, datetime, time as ClockTime, timezone
from zoneinfo import ZoneInfo
import io

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

try:
    import metpy.calc as mpcalc
    from metpy.plots import SkewT
    from metpy.units import units
except ImportError:
    mpcalc = None
    SkewT = None
    units = None


def _metric_value(value, unit="", decimals=0):
    """Formata quantidades MetPy, sem exibir NaN como resultado físico."""
    if value is None:
        return "—"
    try:
        number = float(np.asarray(value.magnitude).squeeze())
        if not np.isfinite(number):
            return "—"
        return f"{number:.{decimals}f}{(' ' + unit) if unit else ''}"
    except (TypeError, ValueError, AttributeError):
        return "—"


def _valid_quantity(value):
    """Devolve None para pressões/temperaturas indefinidas."""
    if value is None:
        return None
    try:
        if not np.all(np.isfinite(np.asarray(value.magnitude))):
            return None
        return value
    except (TypeError, ValueError, AttributeError):
        return None


def render_skewt_plot(df, lat, lon, date, hour):
    """Exibe Skew-T e índices de uma parcela de superfície, sem interpolação artificial."""
    if mpcalc is None:
        st.error("A biblioteca MetPy não está instalada. Verifique requirements.txt.")
        return

    required = {"pressure", "temperature", "relative_humidity"}
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        st.warning("Perfil atmosférico indisponível.")
        return
    if not required.issubset(df.columns):
        st.error("Colunas ausentes no perfil: " + ", ".join(sorted(required - set(df.columns))))
        return

    data = df.copy()
    for name in required | {"u_component", "v_component"}:
        if name not in data.columns:
            data[name] = np.nan
        data[name] = pd.to_numeric(data[name], errors="coerce")

    data = data.replace([np.inf, -np.inf], np.nan)
    data = data.dropna(subset=["pressure", "temperature"])
    data = data[(data["pressure"] > 0) & (data["pressure"] <= 1100)]
    data = data.sort_values("pressure", ascending=False)
    data = data.drop_duplicates(subset="pressure").reset_index(drop=True)
    if len(data) < 2:
        st.error("O perfil contém menos de dois níveis válidos de pressão e temperatura.")
        return

    # RH nula/ausente não corresponde a 0%. Valores fora (0, 100] são inválidos.
    rh_values = data["relative_humidity"].to_numpy(dtype=float)
    rh_values[(rh_values <= 0) | (rh_values > 100)] = np.nan

    p = data["pressure"].to_numpy(dtype=float) * units.hectopascal
    T = data["temperature"].to_numpy(dtype=float) * units.degC
    Td_values = np.full(len(data), np.nan)
    rh_mask = np.isfinite(rh_values)
    if rh_mask.any():
        try:
            dew = mpcalc.dewpoint_from_relative_humidity(
                T[rh_mask], rh_values[rh_mask] / 100.0
            ).to("degC")
            Td_values[rh_mask] = np.asarray(dew.magnitude, dtype=float)
        except (ValueError, TypeError) as exc:
            st.warning(f"Não foi possível obter o ponto de orvalho: {exc}")
    Td = Td_values * units.degC

    # Exportação dos níveis efetivamente utilizados no Skew-T.
    # Mantém lacunas como células vazias; não interpola nem inventa medições.
    export_data = data[[
        "pressure", "temperature", "relative_humidity",
        "u_component", "v_component",
    ]].copy()
    export_data["relative_humidity"] = rh_values
    export_data.insert(3, "dewpoint_C", Td_values)
    export_data = export_data.rename(columns={
        "pressure": "pressure_hPa",
        "temperature": "temperature_C",
        "relative_humidity": "relative_humidity_pct",
        "u_component": "wind_u_ms",
        "v_component": "wind_v_ms",
    })
    source_date = df.attrs.get("real_date", date)
    if isinstance(source_date, (datetime, Date)):
        iso_date = source_date.strftime("%Y-%m-%d")
    else:
        iso_date = str(source_date)
    export_data.insert(0, "date_UTC", iso_date)
    export_data.insert(1, "hour_UTC", str(hour))
    export_data.insert(2, "latitude_deg", float(lat))
    export_data.insert(3, "longitude_deg", float(lon))
    export_data.insert(4, "data_source", str(df.attrs.get("source", "Não informada")))
    csv_bytes = export_data.to_csv(index=False, na_rep="", float_format="%.5f").encode("utf-8-sig")
    #    st.download_button(
    #        "Exportar perfil vertical (CSV)",
    #        data=csv_bytes,
    #        file_name=f"climacast_perfil_{iso_date}.csv",
    #        mime="text/csv",
    #        help="Níveis originais do perfil modelado, sem interpolação. "
    #             "Campos vazios representam dados indisponíveis.",
    #    )

    # Para índices de parcela de superfície, todo o perfil deve ter T e Td válidos.
    complete_thermo = np.all(np.isfinite(Td_values))
    cape = cin = lcl_p = lcl_t = lfc_p = lfc_t = el_p = el_t = None
    li = k_idx = pw = prof = None
    failures = []

    if complete_thermo:
        try:
            prof = mpcalc.parcel_profile(p, T[0], Td[0]).to("degC")
            lcl_p, lcl_t = mpcalc.lcl(p[0], T[0], Td[0])
            lcl_p, lcl_t = _valid_quantity(lcl_p), _valid_quantity(lcl_t)
        except (ValueError, TypeError, IndexError) as exc:
            prof = None
            failures.append(f"Perfil da parcela/LCL: {exc}")

        if prof is not None:
            try:
                cape, cin = mpcalc.surface_based_cape_cin(p, T, Td)
                cape, cin = _valid_quantity(cape), _valid_quantity(cin)
            except (ValueError, TypeError, IndexError) as exc:
                failures.append(f"CAPE/CIN: {exc}")
            try:
                lfc_p, lfc_t = mpcalc.lfc(p, T, Td, parcel_temperature_profile=prof)
                lfc_p, lfc_t = _valid_quantity(lfc_p), _valid_quantity(lfc_t)
            except (ValueError, TypeError, IndexError) as exc:
                failures.append(f"LFC: {exc}")
            try:
                el_p, el_t = mpcalc.el(p, T, Td, parcel_temperature_profile=prof)
                el_p, el_t = _valid_quantity(el_p), _valid_quantity(el_t)
            except (ValueError, TypeError, IndexError) as exc:
                failures.append(f"EL: {exc}")
            try:
                li_result = mpcalc.lifted_index(p, T, prof)
                li = _valid_quantity(li_result[0] if np.ndim(li_result.magnitude) else li_result)
            except (ValueError, TypeError, IndexError) as exc:
                failures.append(f"LI: {exc}")
        try:
            # Água precipitável na camada amostrada, sem integração de Pint.Quantity.
            # p está ordenada da maior para a menor pressão.
            p_pa = np.asarray(p.to("pascal").magnitude, dtype=float)
            e_pa = np.asarray(
                mpcalc.saturation_vapor_pressure(Td).to("pascal").magnitude,
                dtype=float,
            )
            epsilon = 0.6219569  # Razão entre massas molares do vapor e do ar seco
            q = epsilon * e_pa / (p_pa - (1.0 - epsilon) * e_pa)
            if (len(p_pa) < 2 or not np.all(np.isfinite(q))
                    or np.any(p_pa <= e_pa)
                    or not np.all(np.diff(p_pa) < 0)):
                raise ValueError("Perfil inválido para integrar a água precipitável.")
            integrate = np.trapezoid if hasattr(np, "trapezoid") else np.trapz
            pw_mm = -float(integrate(q, p_pa)) / 9.80665
            pw = _valid_quantity(pw_mm * units.millimeter)
        except (ValueError, TypeError, IndexError, AttributeError) as exc:
            failures.append(f"Água precipitável: {exc}")
        try:
            k_idx = _valid_quantity(mpcalc.k_index(p, T, Td))
        except (ValueError, TypeError, IndexError) as exc:
            failures.append(f"K-Index: {exc}")
    else:
        st.info(
            "Há níveis sem umidade relativa válida. O perfil de temperatura é exibido, "
            "mas os índices termodinâmicos não são calculados com dados incompletos."
        )

    if failures:
        with st.expander("Detalhes dos cálculos indisponíveis"):
            for failure in failures:
                st.write(failure)

    # Aparência alinhada às caixas informativas da página inicial.
    st.markdown("""
    <style>
    .st-key-skewt_indices_box {
        background: rgba(255, 255, 255, 0.92) !important;
        border: 1px solid rgba(180, 190, 200, 0.50) !important;
        border-radius: 8px !important;
        padding: 12px 16px !important;
    }
    .st-key-skewt_indices_box [data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.55);
        border-radius: 6px;
        padding: 5px 8px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.subheader("Índices termodinâmicos")
    with st.container(border=True, key="skewt_indices_box"):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("SBCAPE", _metric_value(cape, "J/kg"), help="CAPE de parcela iniciada na superfície modelada.")
        c2.metric("SBCIN", _metric_value(cin, "J/kg"), help="Inibição convectiva da parcela de superfície; valores usualmente negativos.")
        c3.metric("LCL", _metric_value(lcl_p, "hPa"), help="Nível de condensação por levantamento, expresso em pressão.")
        c4.metric("LFC", _metric_value(lfc_p, "hPa"), help="Nível de convecção livre estimado pelo MetPy; pode não existir.")
        c5, c6, c7, c8 = st.columns(4)
        c5.metric("LI", _metric_value(li, "°C", 1), help="Índice de levantamento, aproximadamente T ambiente menos T da parcela em 500 hPa.")
        c6.metric("K-Index", _metric_value(k_idx, "°C", 1), help="Índice baseado em temperaturas e pontos de orvalho de níveis fixos.")
        c7.metric("Água precipitável", _metric_value(pw, "mm", 1), help="Integral de vapor d'água apenas na camada vertical amostrada.")
        c8.metric("EL", _metric_value(el_p, "hPa"), help="Nível de equilíbrio, quando identificado no perfil disponível.")

    st.markdown(
        "<div style='background:rgba(255,255,255,0.88);"
        "border:1px solid rgba(180,190,200,0.50);border-radius:8px;"
        "padding:10px 16px;margin:10px 0 14px 0;"
        "color:#526171;font-size:0.82rem;line-height:1.5;'>"
        "<b>Nota científica:</b> Índices de parcela de superfície calculados "
        "com MetPy a partir de perfis modelados. "
        "Resultados não equivalem a uma radiossondagem e dependem da "
        "resolução vertical e da disponibilidade de todos os níveis. "
        "‘—’ indica resultado indisponível ou indefinido."
        "</div>",
        unsafe_allow_html=True,
    )

    fig = plt.figure(figsize=(9, 9))
    try:
        skew = SkewT(fig, rotation=45)
        skew.plot(p, T, "r", linewidth=2, label="Temperatura")
        skew.plot(p, Td, "g", linewidth=2, label="Ponto de orvalho")

        if prof is not None:
            skew.plot(p, prof, "k--", linewidth=1.5, label="Parcela de superfície")
            if cape is not None and float(cape.magnitude) > 0:
                skew.shade_cape(p, T, prof, alpha=0.18)
            if cin is not None and float(cin.magnitude) < 0:
                skew.shade_cin(p, T, prof, dewpoint=Td, alpha=0.18)

        if lcl_p is not None and lcl_t is not None:
            skew.plot(lcl_p, lcl_t, "ko", label="LCL")
        if lfc_p is not None and lfc_t is not None:
            skew.plot(lfc_p, lfc_t, "bo", label="LFC")
        if el_p is not None and el_t is not None:
            skew.plot(el_p, el_t, "ro", label="EL")

        # Barbelas somente onde ambas as componentes são fornecidas.
        u = data["u_component"].to_numpy(dtype=float)
        v = data["v_component"].to_numpy(dtype=float)
        valid_wind = np.isfinite(u) & np.isfinite(v)
        wind_indices = np.where(valid_wind)[0][::2]
        if len(wind_indices):
            skew.plot_barbs(
                p[wind_indices],
                (u[wind_indices] * units("m/s")).to("knots"),
                (v[wind_indices] * units("m/s")).to("knots"),
            )

        skew.plot_dry_adiabats(alpha=0.25)
        skew.plot_moist_adiabats(alpha=0.25)
        skew.plot_mixing_lines(linestyle="dotted", alpha=0.3)
        skew.ax.set_ylim(max(1000, float(p[0].magnitude) + 20), 100)
        skew.ax.set_xlim(-40, 50)
        skew.ax.set_ylabel("Pressão (hPa)")
        skew.ax.set_xlabel("Temperatura (°C)")
        skew.ax.grid(alpha=0.25)

        # Cabeçalho: informação temporal, geográfica e proveniência do perfil.
        observed_date = df.attrs.get("real_date", date)
        if isinstance(observed_date, datetime):
            day_utc = observed_date.date()
        elif isinstance(observed_date, Date):
            day_utc = observed_date
        else:
            day_utc = datetime.fromisoformat(str(observed_date)).date()

        moment_utc = datetime.combine(
            day_utc, ClockTime(hour=int(hour)), tzinfo=timezone.utc
        )
        moment_brt = moment_utc.astimezone(ZoneInfo("America/Sao_Paulo"))
        date_str = moment_utc.strftime("%d/%m/%Y")
        local_str = moment_brt.strftime("%d/%m/%Y %H:%M")

        def coordinate_label(value, positive, negative):
            return f"{abs(float(value)):.2f}° {positive if value >= 0 else negative}"

        lat_str = coordinate_label(lat, "N", "S")
        lon_str = coordinate_label(lon, "L", "O")

        # A fonte vem dos metadados do handler; nenhum modelo é inferido.
        source = str(df.attrs.get("source") or "Fonte não informada")
        source = source.replace("(modelo não fixado)", "").strip(" -|,")
        source = source.replace("(Modelo não fixado)", "").strip(" -|,")
        fig.suptitle(
            "Diagrama Termodinâmico Skew-T/log-P\n"
            f"{date_str} {int(hour):02d}:00 UTC | Horário local: {local_str}\n"
            f"Lat.: {lat_str} | Lon.: {lon_str}\n"
            f"Fonte: {source} | Perfil atmosférico modelado",
            fontsize=10.5, x=0.12, y=0.99, ha="left", va="top",
        )
        skew.ax.legend(loc="upper right", fontsize=9)
        st.pyplot(fig)

        image_bytes = io.BytesIO()
        fig.savefig(image_bytes, format="png", dpi=150, bbox_inches="tight")
        st.download_button(
            "Baixar gráfico (PNG)",
            image_bytes.getvalue(),
            file_name="skewt.png",
            mime="image/png",
        )
    except Exception as exc:
        st.error(f"Não foi possível desenhar o Skew-T: {type(exc).__name__}: {exc}")
    finally:
        plt.close(fig)
