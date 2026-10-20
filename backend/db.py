"""
Prisma Database Service for Supabase PostgreSQL
Persists uploaded datasets and employees, and provides AI-grounded database queries.
"""

import os
import asyncio
import logging
import threading
from typing import Optional, Dict, Any, List
from prisma import Prisma

logger = logging.getLogger(__name__)


def save_dataset_in_background(df, filename: str, total: int, attr_count: int, ret_count: int, attr_rate: float):
    """
    Launch a background thread to persist the uploaded dataset and employee rows
    into Supabase PostgreSQL via Prisma without blocking the HTTP upload response.
    """
    def _worker():
        try:
            asyncio.run(
                _async_save_dataset(
                    df.copy(),
                    filename,
                    total,
                    attr_count,
                    ret_count,
                    attr_rate,
                )
            )
        except Exception as e:
            logger.warning(f"Could not persist dataset to Supabase PostgreSQL: {e}")

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()


async def _async_save_dataset(df, filename: str, total: int, attr_count: int, ret_count: int, attr_rate: float):
    db = Prisma()
    await db.connect()
    try:
        # 1. Create UploadedDataset record
        dataset_record = await db.uploadeddataset.create(
            data={
                "filename": filename,
                "totalEmployees": total,
                "attritionCount": attr_count,
                "retentionCount": ret_count,
                "attritionRate": float(attr_rate),
            }
        )
        dataset_id = dataset_record.id
        logger.info(f"Created UploadedDataset '{filename}' in Supabase: {dataset_id}")

        # 2. Batch insert employees in chunks of 500
        chunk_size = 500
        total_rows = len(df)

        for i in range(0, total_rows, chunk_size):
            chunk = df.iloc[i : i + chunk_size]
            records = []
            for _, row in chunk.iterrows():
                emp_no = str(row.get("EmployeeNumber", row.get("EmployeeID", "N/A"))).strip()

                reasons = []
                if str(row.get("OverTime", "")).lower() in ("yes", "y", "true", "1"):
                    reasons.append("Works Overtime")
                try:
                    if float(row.get("MonthlyIncome", 99999)) < 5000:
                        reasons.append("Low Monthly Income (<₹5,000)")
                except Exception:
                    pass
                try:
                    if int(row.get("YearsAtCompany", 99)) <= 2:
                        reasons.append("Short Tenure (≤2 yrs)")
                except Exception:
                    pass
                try:
                    if int(row.get("JobSatisfaction", 3)) <= 2:
                        reasons.append("Low Job Satisfaction")
                except Exception:
                    pass
                try:
                    if int(row.get("EnvironmentSatisfaction", 3)) <= 2:
                        reasons.append("Low Workplace Satisfaction")
                except Exception:
                    pass
                try:
                    if int(row.get("StockOptionLevel", 1)) == 0:
                        reasons.append("Zero Stock Options")
                except Exception:
                    pass
                try:
                    if int(row.get("Age", 99)) <= 25 and int(row.get("Age", 99)) > 0:
                        reasons.append("Early Career Age (≤25)")
                except Exception:
                    pass
                try:
                    if int(row.get("WorkLifeBalance", 3)) <= 1:
                        reasons.append("Poor Work-Life Balance")
                except Exception:
                    pass

                def _s_int(v, d=0):
                    try:
                        return int(float(v))
                    except Exception:
                        return d

                def _s_float(v, d=0.0):
                    try:
                        return float(v)
                    except Exception:
                        return d

                records.append({
                    "datasetId": dataset_id,
                    "employeeNumber": emp_no,
                    "age": _s_int(row.get("Age", 30)),
                    "gender": str(row.get("Gender", "Not Specified")),
                    "maritalStatus": str(row.get("MaritalStatus", "Single")),
                    "department": str(row.get("Department", "General")),
                    "jobRole": str(row.get("JobRole", "Employee")),
                    "monthlyIncome": _s_float(row.get("MonthlyIncome", 5000.0)),
                    "overtime": str(row.get("OverTime", "No")),
                    "yearsAtCompany": _s_int(row.get("YearsAtCompany", 0)),
                    "distanceFromHome": _s_int(row.get("DistanceFromHome", 5)),
                    "businessTravel": str(row.get("BusinessTravel", "Travel_Rarely")),
                    "jobSatisfaction": _s_int(row.get("JobSatisfaction", 3)),
                    "jobSatisfactionLabel": str(row.get("JobSatisfactionLabel", "Medium")),
                    "envSatisfaction": _s_int(row.get("EnvironmentSatisfaction", 3)),
                    "envSatisfactionLabel": str(row.get("EnvSatisfactionLabel", "Medium")),
                    "workLifeBalance": _s_int(row.get("WorkLifeBalance", 3)),
                    "workLifeBalanceLabel": str(row.get("WorkLifeBalanceLabel", "Medium")),
                    "stockOptionLevel": _s_int(row.get("StockOptionLevel", 0)),
                    "riskScore": _s_int(row.get("RiskScore", len(reasons))),
                    "riskLevel": str(row.get("RiskLevel", "Low")),
                    "attrition": str(row.get("Attrition", "No")),
                    "attritionFlag": bool(row.get("AttritionFlag", False)),
                    "riskReasons": reasons,
                })

            if records:
                await db.employee.create_many(data=records)
                logger.info(f"Persisted {len(records)} employees into Supabase chunk [{i}:{i + len(records)}]")
    finally:
        await db.disconnect()


def find_employee_in_db(emp_id: str) -> Optional[Dict[str, Any]]:
    """Synchronous helper to look up an employee from the Prisma Supabase database."""
    try:
        return asyncio.run(_async_find_employee(emp_id))
    except Exception as e:
        logger.warning(f"Prisma DB query failed: {e}")
        return None


async def _async_find_employee(emp_id: str) -> Optional[Dict[str, Any]]:
    db = Prisma()
    await db.connect()
    try:
        target = str(emp_id).strip().lstrip("#")

        emp = await db.employee.find_first(
            where={
                "employeeNumber": {
                    "equals": target,
                    "mode": "insensitive",
                }
            },
            order={
                "createdAt": "desc",
            }
        )

        if not emp:
            return None

        return {
            "employee_number": emp.employeeNumber,
            "age": emp.age,
            "gender": emp.gender or "Not Specified",
            "marital_status": emp.maritalStatus or "Single",
            "department": emp.department,
            "job_role": emp.jobRole,
            "monthly_income": emp.monthlyIncome,
            "overtime": emp.overtime,
            "years_at_company": emp.yearsAtCompany,
            "distance_from_home": emp.distanceFromHome or 0,
            "business_travel": emp.businessTravel or "Travel_Rarely",
            "job_satisfaction": emp.jobSatisfaction,
            "job_satisfaction_label": emp.jobSatisfactionLabel or "Medium",
            "env_satisfaction": emp.envSatisfaction,
            "env_satisfaction_label": emp.envSatisfactionLabel or "Medium",
            "work_life_balance": emp.workLifeBalance,
            "work_life_balance_label": emp.workLifeBalanceLabel or "Medium",
            "stock_option_level": emp.stockOptionLevel,
            "risk_score": emp.riskScore,
            "risk_level": emp.riskLevel,
            "attrition": emp.attrition,
            "attrition_flag": emp.attritionFlag,
            "risk_reasons": emp.riskReasons or [],
            "source": "supabase_prisma_db",
        }
    finally:
        await db.disconnect()
