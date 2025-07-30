from database.repositories.user_repository import UserRepository
from database.repositories.risk_repository import RiskRepository
from database.repositories.report_repository import ReportRepository

class RepositoryFactory:
    """Factory class to manage repository instances"""
    
    def __init__(self):
        self._user_repo = None
        self._risk_repo = None
        self._report_repo = None
    
    @property
    def user_repository(self) -> UserRepository:
        """Get user repository instance"""
        if self._user_repo is None:
            self._user_repo = UserRepository()
        return self._user_repo
    
    @property
    def risk_repository(self) -> RiskRepository:
        """Get risk repository instance"""
        if self._risk_repo is None:
            self._risk_repo = RiskRepository()
        return self._risk_repo
    
    @property
    def report_repository(self) -> ReportRepository:
        """Get report repository instance"""
        if self._report_repo is None:
            self._report_repo = ReportRepository()
        return self._report_repo

# Global repository factory instance
repo_factory = RepositoryFactory()