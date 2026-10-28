"""
Phase 5 End-to-End Operational Verification Script.
Tests:
1. Deterministic flood risk engine with IMD & CWC criteria.
2. Deterministic landslide risk engine with GSI terrain slope criteria.
3. Multi-hazard district synthesis and indicative disclaimers.
4. Multi-signal explainable confidence scoring.
5. Spatio-temporal and TF-IDF duplicate clustering.
6. scikit-learn ML model benchmark (accuracy, F1, confusion matrix, feature importances).
7. Situational awareness overview integration.
"""
import asyncio
import httpx

BASE_URL = "http://localhost:8000/api/v1"

async def test_full_phase5_e2e():
    print("=" * 70)
    print("STARTING PHASE 5 INTELLIGENCE & RISK ENGINE E2E VERIFICATION")
    print("=" * 70)

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        # Step 1: Deterministic Flood Risk Engine (IMD & CWC)
        print("\n[Step 1] Testing Deterministic Flood Risk Engine (IMD & CWC criteria)...")
        res_flood = await client.get("/intelligence/risk/flood", params={
            "rainfall_1h_mm": 55.0,
            "rainfall_24h_mm": 130.0,
            "water_level_m": 4.8,
            "danger_mark_m": 4.5,
            "district_id": 2,
        })
        assert res_flood.status_code == 200, f"Flood risk failed: {res_flood.text}"
        f_data = res_flood.json()
        print(f" -> Hazard: {f_data['hazardType']}, Risk Level: {f_data['riskLevel']}")
        print(f" -> Factors: {f_data['factors']}")
        print(f" -> Metrics: {f_data['metrics']}")
        print(f" -> Disclaimer: '{f_data['disclaimer']}'")
        assert f_data["hazardType"] == "FLOOD"
        assert f_data["isOfficialWarning"] is False
        assert f_data["riskLevel"] in ["HIGH", "CRITICAL"]
        assert "Indicative risk" in f_data["disclaimer"]
        print(" -> Flood Risk Engine successfully verified.")

        # Step 2: Deterministic Landslide Risk Engine (GSI Terrain Slope & API)
        print("\n[Step 2] Testing Deterministic Landslide Risk Engine (GSI criteria)...")
        # Mountainous Raigad (District 5)
        res_landslide = await client.get("/intelligence/risk/landslide", params={
            "rainfall_72h_mm": 270.0,
            "rainfall_24h_mm": 90.0,
            "district_id": 5,
        })
        assert res_landslide.status_code == 200, f"Landslide risk failed: {res_landslide.text}"
        l_data = res_landslide.json()
        print(f" -> Raigad Hazard: {l_data['hazardType']}, Risk Level: {l_data['riskLevel']}")
        print(f" -> Terrain Slope Factor: {l_data['factors']['terrainSlope']}")
        print(f" -> Antecedent Rain Factor: {l_data['factors']['rainfallAccumulation']}")
        print(f" -> Recommended Action: {l_data['recommendedAction']}")
        assert l_data["hazardType"] == "LANDSLIDE"
        assert l_data["riskLevel"] in ["HIGH", "CRITICAL"]
        assert l_data["isOfficialWarning"] is False

        # Flat coastal plains Mumbai City (District 1) -> Low
        res_flat = await client.get("/intelligence/risk/landslide", params={
            "rainfall_72h_mm": 270.0,
            "district_id": 1,
        })
        assert res_flat.status_code == 200
        assert res_flat.json()["riskLevel"] == "LOW"
        print(" -> Flat coastal plain (Mumbai City) correctly evaluated as LOW landslide susceptibility.")

        # Step 3: District Multi-Hazard Indicative Risk Synthesis
        print("\n[Step 3] Testing District Multi-Hazard Indicative Risk Synthesis (/risk/district/2)...")
        res_dist = await client.get("/intelligence/risk/district/2")
        assert res_dist.status_code == 200, f"District risk failed: {res_dist.text}"
        d_data = res_dist.json()
        print(f" -> District: {d_data['district']['name']}")
        print(f" -> Composite Indicative Risk: {d_data['composite_risk_level']}")
        print(f" -> Flood Risk: {d_data['hazards']['flood']['riskLevel']}")
        print(f" -> Landslide Risk: {d_data['hazards']['landslide']['riskLevel']}")
        print(f" -> ML Model Concordance Prediction: {d_data['ml_comparative_baseline']['predicted_risk_level']}")
        assert "composite_risk_level" in d_data
        assert d_data["isOfficialWarning"] is False
        assert "Indicative risk" in d_data["indicative_disclaimer"]
        print(" -> Multi-hazard district synthesis verified.")

        # Step 4: Multi-Signal Explainable Report Confidence Scoring
        print("\n[Step 4] Testing Multi-Signal Explainable Report Confidence Scoring...")
        eval_payload = {
            "description": "Flash flood near Milan subway underpass with trapped cars and water entering low-lying premises.",
            "latitude": 19.098,
            "longitude": 72.843,
            "has_media": True,
            "user_role": "citizen",
            "corroborating_reports_count": 2,
            "nearby_sensor_active": True,
            "rainfall_observed_mm": 54.0,
            "hazard_type": "flood",
        }
        res_conf = await client.post("/intelligence/confidence/evaluate", json=eval_payload)
        assert res_conf.status_code == 200, f"Confidence failed: {res_conf.text}"
        c_data = res_conf.json()
        print(f" -> Confidence Level: {c_data['confidence_level']} ({c_data['confidence_score']})")
        print(" -> Itemized Factor Deltas:")
        for factor in c_data["contributing_factors"]:
            print(f"    - {factor['signal']}: {factor['detail']} ({factor['delta']:+0.2f})")
        assert c_data["confidence_level"] in ["MEDIUM", "HIGH"]
        assert c_data["confidence_score"] >= 0.70
        print(" -> Explainable confidence breakdown verified.")

        # Step 5: Spatio-Temporal & TF-IDF Duplicate Clustering
        print("\n[Step 5] Testing Spatio-Temporal & TF-IDF Duplicate Clustering...")
        res_dup = await client.post("/intelligence/duplicates/cluster", json={
            "district_id": 2,
            "max_distance_meters": 600.0,
            "max_time_delta_seconds": 7200.0,
        })
        assert res_dup.status_code == 200, f"Duplicate cluster failed: {res_dup.text}"
        dup_data = res_dup.json()
        print(f" -> Total Active Reports: {dup_data['total_active_reports']}")
        print(f" -> Total Spatial Clusters: {dup_data['total_clusters']}")
        print(f" -> Suspected Duplicate Clusters: {dup_data['duplicate_clusters_count']}")
        print(f" -> Policy Confirmation: '{dup_data['policy']}'")
        assert "Suspected duplicate candidates are grouped" in dup_data["policy"]
        print(" -> Duplicate clustering verified.")

        # Step 6: scikit-learn ML Baseline Benchmark & Comparison
        print("\n[Step 6] Testing scikit-learn ML Model Benchmark vs Rule-Based Engine...")
        res_ml = await client.get("/intelligence/ml/benchmark")
        assert res_ml.status_code == 200, f"ML benchmark failed: {res_ml.text}"
        ml_data = res_ml.json()
        ds = ml_data["dataset_summary"]
        rf = ml_data["random_forest_metrics"]
        print(f" -> Benchmark Dataset Size: {ds['total_samples']} samples (Train: {ds['train_samples']}, Test: {ds['test_samples']})")
        print(f" -> Geographic Coverage: {ds['geographic_coverage']}")
        print(f" -> Class Distribution: {ds['class_distribution']}")
        print(f" -> Random Forest Accuracy: {rf['accuracy'] * 100:.1f}%")
        print(f" -> Macro F1-Score: {rf['macro_f1']:.3f}, Weighted F1: {rf['weighted_f1']:.3f}")
        print(f" -> Macro Precision: {rf['macro_precision']:.3f}, Macro Recall: {rf['macro_recall']:.3f}")
        print(" -> Top 3 Feature Importances:")
        for fi in ml_data["feature_importances"][:3]:
            print(f"    - {fi['feature']}: {fi['importance'] * 100:.1f}%")
        assert rf["accuracy"] >= 0.85
        assert rf["macro_f1"] >= 0.80
        assert "Benchmark records are simulated" in ml_data["disclaimer"]
        print(" -> ML baseline benchmark verified.")

        # Step 7: Overview Situational Awareness Synthesis Integration
        print("\n[Step 7] Verifying structured indicative risk integration into Overview API...")
        res_overview = await client.get("/overview", params={"district_id": 2})
        assert res_overview.status_code == 200
        o_data = res_overview.json()
        risk_est = o_data["risk_estimates"]
        assert "structured_flood" in risk_est
        assert "structured_landslide" in risk_est
        assert "indicative_disclaimer" in risk_est
        print(f" -> Overview Structured Flood Risk: {risk_est['structured_flood']['riskLevel']}")
        print(f" -> Overview Structured Landslide Risk: {risk_est['structured_landslide']['riskLevel']}")
        print(f" -> Overview Disclaimer: '{risk_est['indicative_disclaimer']}'")
        print(" -> Overview API integration verified.")

    print("\n" + "=" * 70)
    print("PHASE 5 INTELLIGENCE & RISK ENGINE E2E TEST: 100% PASSED")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_full_phase5_e2e())
