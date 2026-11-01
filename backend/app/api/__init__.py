from fastapi import APIRouter
from .health import router as health_router
from .reference import router as reference_router
from .questions import router as questions_router
from .paper import router as paper_router
from .question_bank import router as bank_router
from .blueprint import router as blueprint_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="", tags=["Health"])
api_router.include_router(reference_router, prefix="/reference", tags=["Reference"])
api_router.include_router(questions_router, prefix="/questions", tags=["Questions"])
api_router.include_router(paper_router, prefix="/paper", tags=["Paper"])
api_router.include_router(bank_router, prefix="/bank", tags=["Question Bank"])
api_router.include_router(blueprint_router, prefix="/blueprint", tags=["Exam Blueprint"])

