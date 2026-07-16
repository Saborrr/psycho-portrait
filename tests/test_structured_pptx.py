from pathlib import Path

from app.parser import parse_pptx
from app.models import EmployeeInfo, MethodScores, ParsedProfile
from app.pptx_structured import _parse_employee_table


def test_structured_sample_still_parses():
    path = Path(__file__).parent.parent / "samples" / "sample_efko_full.pptx"
    profile = parse_pptx(str(path), source_filename=path.name)
    assert profile.methods.mmpi is not None
    assert profile.methods.efko is not None
    assert profile.source_filename == path.name


def test_gender_from_divorced_family_status():
    male = ParsedProfile(employee=EmployeeInfo(), methods=MethodScores())
    female = ParsedProfile(employee=EmployeeInfo(), methods=MethodScores())
    prefix = [["Возраст, место проживания", "35 лет, город"]]
    assert _parse_employee_table(prefix + [["Семейное положение, дети", "Разведен, есть дети"]], male)
    assert _parse_employee_table(prefix + [["Семейное положение, дети", "Разведена, есть дети"]], female)
    assert male.employee.gender == "мужской"
    assert female.employee.gender == "женский"
