from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import csv
from io import StringIO
from fastapi.responses import StreamingResponse
import uuid

from app.core.database import get_db
from app.core.logging import logger
from app.models.models import Survey, SurveyResponse
from app.schemas.survey import SurveyResponseSchema, SurveyUpdate, SurveyAnswerSubmit, SurveyAnswerResponse

router = APIRouter(prefix="/surveys", tags=["surveys"])


@router.get("/event/{event_id}", response_model=SurveyResponseSchema)
async def get_event_survey(
    event_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """获取事件的调查配置"""
    result = await db.execute(
        Survey.__table__.select().where(Survey.event_id == event_id)
    )
    survey = result.first()

    if not survey:
        # 创建默认调查
        survey = Survey(
            id=uuid.uuid4(),
            event_id=event_id,
            enabled=False,
            title="活动问卷调查",
            questions=[]
        )
        db.add(survey)
        await db.commit()
        await db.refresh(survey)

    return survey


@router.put("/event/{event_id}", response_model=SurveyResponseSchema)
async def update_event_survey(
    event_id: UUID,
    survey_data: SurveyUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新事件的调查配置"""
    try:
        result = await db.execute(
            Survey.__table__.select().where(Survey.event_id == event_id)
        )
        survey = result.first()

        if not survey:
            survey = Survey(
                id=uuid.uuid4(),
                event_id=event_id,
                **survey_data.dict()
            )
            db.add(survey)
        else:
            for field, value in survey_data.dict().items():
                setattr(survey, field, value)

        await db.commit()
        await db.refresh(survey)
        return survey

    except Exception as e:
        logger.error(f"更新调查配置失败: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"更新调查配置失败: {str(e)}")


@router.post("/responses", response_model=SurveyAnswerResponse)
async def submit_survey_response(
    answer_data: SurveyAnswerSubmit,
    db: AsyncSession = Depends(get_db)
):
    """提交调查回答"""
    try:
        response = SurveyResponse(
            id=uuid.uuid4(),
            event_id=answer_data.event_id,
            session_id=answer_data.session_id,
            answers=answer_data.answers
        )

        db.add(response)
        await db.commit()
        await db.refresh(response)
        return response

    except Exception as e:
        logger.error(f"提交调查回答失败: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"提交调查回答失败: {str(e)}")


@router.get("/responses/session/{session_id}", response_model=List[SurveyAnswerResponse])
async def get_session_survey_responses(
    session_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """获取某次会话的回答"""
    result = await db.execute(
        SurveyResponse.__table__.select().where(SurveyResponse.session_id == session_id)
    )
    responses = result.all()
    return [SurveyAnswerResponse.from_orm(resp) for resp in responses]


@router.get("/responses/export/{event_id}")
async def export_survey_responses(
    event_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """导出调查回答为CSV"""
    try:
        # 获取调查配置
        survey_result = await db.execute(
            Survey.__table__.select().where(Survey.event_id == event_id)
        )
        survey = survey_result.first()

        if not survey:
            raise HTTPException(status_code=404, detail="该事件没有调查配置")

        # 获取所有回答
        responses_result = await db.execute(
            SurveyResponse.__table__.select().where(SurveyResponse.event_id == event_id)
        )
        responses = responses_result.all()

        # 创建CSV
        output = StringIO()
        writer = csv.writer(output)

        # 表头
        headers = ["会话ID", "提交时间"]
        question_ids = []
        for question in survey.questions:
            headers.append(question["text"])
            question_ids.append(question["id"])
        writer.writerow(headers)

        # 写入数据
        for resp in responses:
            row = [
                str(resp.session_id),
                resp.created_at.strftime("%Y-%m-%d %H:%M:%S")
            ]
            for qid in question_ids:
                row.append(resp.answers.get(qid, ""))
            writer.writerow(row)

        output.seek(0)

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=survey_responses_{event_id}.csv"}
        )

    except Exception as e:
        logger.error(f"导出调查回答失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")