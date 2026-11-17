"""PDF Research Report Generator using ReportLab.

Generates a structured, publication-style PDF report directly from real processed database
records (study area, datasets & citations, satellite composites, glacial lake inventory,
historical change statistics, deep learning evaluation status, GLOF susceptibility screening,
hydraulic scenario status, OSM exposure analysis, scientific limitations and references).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..config import get_settings
from ..models import (
    AnnualIndicator,
    ChangeDetectionResult,
    ExposureResult,
    FloodScenario,
    GlacialLake,
    LakeObservation,
    ModelTrainingRun,
    RasterAsset,
    Report,
    SusceptibilityAssessment,
    TerrainAnalysis,
)
from ..study_area import DISASTER_CONTEXT, STUDY_BBOX
from .glof_service import CRITERIA
from .sensors import SENSORS

settings = get_settings()


def generate_pdf_report(db, title: str | None = None, sections: list[str] | None = None) -> Report:
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    report_title = title or "GlacioGuard AI: Kedarnath Region GLOF Susceptibility & Environmental Change Assessment (2000–2026)"
    selected = set(sections or [
        "overview", "study_area", "methodology", "datasets", "observations",
        "change_detection", "deep_learning", "susceptibility", "flood", "exposure", "limitations", "references"
    ])

    out_path = settings.reports_dir / f"glacioguard_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.pdf"
    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=report_title,
    )

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=16, leading=20, textColor=colors.HexColor("#0f172a"), spaceAfter=6)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12, leading=15, textColor=colors.HexColor("#0369a1"), spaceBefore=10, spaceAfter=4)
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontSize=9.5, leading=13, spaceAfter=5)
    small = ParagraphStyle("Small", parent=styles["BodyText"], fontSize=8, leading=10.5, textColor=colors.HexColor("#334155"), spaceAfter=4)

    story = []
    story.append(Paragraph(report_title, h1))
    story.append(Paragraph(f"Generated UTC: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%SZ')} | Projection: WGS 84 / UTM Zone 44N (EPSG:32644)", small))
    story.append(Spacer(1, 4 * mm))

    def _table(rows):
        t = Table(rows, hAlign="LEFT")
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        return t

    if "overview" in selected or "study_area" in selected:
        story.append(Paragraph("1. Project Overview & Study Area", h2))
        story.append(Paragraph(
            f"Study Area: Kedarnath–Chorabari Glacier–Gandhi Sarovar–Mandakini River Basin, Uttarakhand, India "
            f"(Bounding Box: {STUDY_BBOX[0]}°E–{STUDY_BBOX[2]}°E, {STUDY_BBOX[1]}°N–{STUDY_BBOX[3]}°N). "
            "All metric area and distance computations are performed in UTM Zone 44N (EPSG:32644). "
            "Year 2026 observations are treated strictly as year-to-date.", body
        ))
        story.append(Paragraph(f"<b>Scientific Context (June 2013 Disaster):</b> {DISASTER_CONTEXT}", body))

    if "datasets" in selected or "methodology" in selected:
        story.append(Paragraph("2. Satellite Datasets & Sensor Harmonisation", h2))
        ds_rows = [["Mission", "Collection", "Resolution", "Operational Window"]]
        for s in SENSORS.values():
            ds_rows.append([
                s.label, s.gee_collection,
                ", ".join(f"{k}:{v}m" for k, v in list(s.native_resolution_m.items())[:3]),
                f"{s.operational[0]} to {s.operational[1] or 'present'}",
            ])
        story.append(_table(ds_rows))
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(
            "Cloud/shadow/fill masking is applied per-pixel via QA_PIXEL (Landsat Collection 2 Level-2) and SCL "
            "(Sentinel-2 L2A). Post-May 2003 Landsat 7 ETM+ Scan Line Corrector (SLC-off) wedge gaps are flagged as "
            "fill/NoData and excluded from valid pixel fractions.", small
        ))

    if "observations" in selected:
        story.append(Paragraph("3. Processed Satellite Composites & Terrain Analysis", h2))
        comps = db.query(RasterAsset).filter_by(kind="composite").order_by(RasterAsset.year).all()
        if comps:
            c_rows = [["Year", "Mission", "Region", "Resolution (m)", "Valid Fraction", "Scenes"]]
            for c in comps:
                p = c.processing or {}
                c_rows.append([
                    str(c.year or "-"),
                    str(p.get("mission", "-")),
                    str(p.get("region", "full_aoi")),
                    str(c.resolution_x or "-"),
                    f"{(p.get('valid_fraction', 1.0) * 100):.1f}%",
                    str(p.get("scene_count", "-")),
                ])
            story.append(_table(c_rows))
        else:
            story.append(Paragraph("No satellite composites have been generated in the database yet.", body))

        ta = db.query(TerrainAnalysis).order_by(TerrainAnalysis.id.desc()).first()
        if ta and ta.statistics:
            st = ta.statistics
            el = st.get("elevation_m", {})
            sl = st.get("slope_deg", {})
            story.append(Spacer(1, 2 * mm))
            story.append(Paragraph(
                f"<b>DEM & Hydrological Conditioning ({ta.dem_source}):</b> Elevation range {el.get('min', 0):.0f}–{el.get('max', 0):.0f} m "
                f"(mean {el.get('mean', 0):.0f} m); mean slope {sl.get('mean', 0):.1f}° (90th percentile {sl.get('p90', 0):.1f}°); "
                f"mapped D8 stream network length {st.get('stream_length_km', 0):.1f} km (max Strahler order {st.get('max_strahler_order', 0)}).",
                body
            ))

    if "change_detection" in selected:
        story.append(Paragraph("4. Glacial Lake Inventory & Multi-Temporal Change Detection", h2))
        lakes = db.query(GlacialLake).order_by(GlacialLake.lake_code).all()
        if lakes:
            l_rows = [["Lake Code", "Name", "Elevation (m)", "Latest Area (ha)", "Latest Year", "Method"]]
            for lk in lakes:
                obs = db.query(LakeObservation).filter_by(lake_id=lk.id).order_by(LakeObservation.year.desc()).first()
                l_rows.append([
                    lk.lake_code,
                    (lk.name or "-")[:34],
                    f"{lk.elevation_m:.0f}" if lk.elevation_m else "-",
                    f"{obs.area_ha:.3f}" if obs else "-",
                    str(obs.year) if obs else "-",
                    obs.method if obs else "-",
                ])
            story.append(_table(l_rows))
        else:
            story.append(Paragraph("No glacial lakes detected yet.", body))

        cds = db.query(ChangeDetectionResult).order_by(ChangeDetectionResult.id.desc()).limit(8).all()
        if cds:
            story.append(Spacer(1, 2 * mm))
            cd_rows = [["Comparison", "Indicator", "Region", "Gain (ha)", "Loss (ha)", "Net (ha)", "Joint Valid"]]
            for cd in cds:
                s = cd.statistics or {}
                cd_rows.append([
                    f"{cd.year_a} → {cd.year_b}",
                    cd.indicator,
                    cd.region,
                    f"{s.get('area_gain_ha', 0):.2f}",
                    f"{s.get('area_loss_ha', 0):.2f}",
                    f"{s.get('net_change_ha', 0):+.2f}",
                    f"{(s.get('joint_valid_fraction', 0) * 100):.1f}%",
                ])
            story.append(_table(cd_rows))

    if "deep_learning" in selected:
        story.append(Paragraph("5. Deep Learning Segmentation Evaluation (U-Net / DeepLabV3+)", h2))
        runs = db.query(ModelTrainingRun).order_by(ModelTrainingRun.id.desc()).all()
        if runs:
            r_rows = [["Run ID", "Architecture", "Status", "Best Epoch", "Checkpoint"]]
            for r in runs:
                r_rows.append([str(r.id), r.model_type, r.status, str(r.best_epoch or "-"), Path(r.checkpoint_path).name if r.checkpoint_path else "-"])
            story.append(_table(r_rows))
        else:
            story.append(Paragraph(
                "Model status: <b>Awaiting verified training masks</b>. No U-Net or DeepLabV3+ training run has been "
                "completed yet; in accordance with scientific integrity rules, no fabricated metrics are reported.",
                body
            ))

    if "susceptibility" in selected:
        story.append(Paragraph("6. GLOF Susceptibility Screening Assessment", h2))
        story.append(Paragraph(
            "<b>Methodology Disclaimer:</b> Assessments produced by `mcda_screening_v1` are preliminary multi-criteria "
            "screening indices in [0, 1] based on GAPHAZ (2017) / Huggel et al. (2002) / Allen et al. (2019) — they are "
            "NOT trained predictive models and scores are NOT outburst probabilities.",
            small
        ))
        sas = db.query(SusceptibilityAssessment).order_by(SusceptibilityAssessment.score.desc()).all()
        if sas:
            s_rows = [["Lake Code", "Method", "Screening Index", "Category", "Uncertainty Range", "Missing Parameters"]]
            for sa in sas:
                lk = db.get(GlacialLake, sa.lake_id)
                rng = (sa.uncertainty or {}).get("score_range", [None, None])
                s_rows.append([
                    lk.lake_code if lk else str(sa.lake_id),
                    sa.method,
                    f"{sa.score:.3f}" if sa.score is not None else "-",
                    sa.category or "-",
                    f"[{rng[0]:.2f}, {rng[1]:.2f}]" if rng[0] is not None else "-",
                    ", ".join(sa.missing_parameters or []),
                ])
            story.append(_table(s_rows))

    if "flood" in selected or "exposure" in selected:
        story.append(Paragraph("7. Hypothetical Flood Scenarios & Downstream Infrastructure Exposure", h2))
        scens = db.query(FloodScenario).all()
        story.append(Paragraph(f"Configured hypothetical HEC-RAS 2D scenarios: {len(scens)}.", body))
        exps = db.query(ExposureResult).order_by(ExposureResult.id.desc()).limit(3).all()
        for ex in exps:
            st = ex.statistics or {}
            story.append(Paragraph(
                f"<b>Exposure Analysis #{ex.id} ({ex.analysis_type} — potential exposure only, not confirmed damage):</b> "
                f"Buildings: {st.get('buildings', 0)}, Roads: {st.get('road_length_km', 0):.2f} km, "
                f"Bridges: {st.get('bridges', 0)}, Settlements in corridor: {', '.join(st.get('settlements') or ['None'])}.",
                body
            ))

    if "limitations" in selected or "references" in selected:
        story.append(Paragraph("8. Scientific Limitations & Key References", h2))
        story.append(Paragraph(
            "• 30 m spaceborne DEMs (Copernicus GLO-30) represent surface elevation (2011–2015 TanDEM-X epoch) and cannot resolve moraine dam freeboard (<2–5 m), internal ice cores, or sub-aqueous lake bathymetry.<br/>"
            "• Optical indices (MNDWI, NDVI, NDSI) are affected by topographic shadow in steep Himalayan valleys and cross-sensor spectral response differences between Landsat TM/ETM+/OLI and Sentinel-2 MSI.<br/>"
            "• Downstream flood depths and velocities cannot be derived from a DEM alone and require 2D unsteady hydrodynamic simulation (HEC-RAS 2D) with field-calibrated breach parameters.",
            small
        ))
        story.append(Paragraph(
            "<b>References:</b> Allen et al. (2019) Sci. Bull. 64(7); Barnes et al. (2014) Comput. Geosci. 62; "
            "Dobhal et al. (2013) Curr. Sci. 105(2); GAPHAZ (2017) Assessment of Glacier and Permafrost Hazards in Mountain Regions; "
            "Huggel et al. (2002) Can. Geotech. J. 39(2); McFeeters (1996) Int. J. Remote Sens. 17(7); "
            "Rafiq et al. (2019) Geomat. Nat. Hazards Risk 10(1); Ronneberger et al. (2015) MICCAI U-Net; Xu (2006) Int. J. Remote Sens. 27(14).",
            small
        ))

    doc.build(story)
    rep = Report(title=report_title, path=str(out_path), sections=sorted(selected))
    db.add(rep)
    db.commit()
    db.refresh(rep)
    return rep

