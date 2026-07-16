from app.methodology import build_interpretation_payload
from app.models import EmployeeInfo, MMPI, MethodScores, ParsedProfile


def test_user_override_and_social_introversion_levels():
    profile = ParsedProfile(
        employee=EmployeeInfo(position="Начальник отдела"),
        methods=MethodScores(mmpi=MMPI(L=81, F=50, K=50, Mf=70, Si=66, validity="invalid")),
    )
    payload = build_interpretation_payload(profile)
    assert payload["job_context"] == {"is_manager": True}
    assert payload["smil"]["scales"]["L"]["level"] == "профиль ненадежен"
    assert payload["smil"]["scales"]["Mf"]["level"] == "в сторону феминизированности"
    assert payload["smil"]["scales"]["Si"]["level"] == "выраженная интровертированность"
    assert "Начальник отдела" not in str(payload)
