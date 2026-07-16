from app.models import BigFive, DISC, EmployeeInfo, MMPI, MethodScores, ParsedProfile
from app.norms import compute_deviations, format_deviations_md


def test_only_standardized_scales_receive_percentiles():
    profile = ParsedProfile(
        employee=EmployeeInfo(),
        methods=MethodScores(
            mmpi=MMPI(Hs=70),
            big_five=BigFive(scale="raw", openness=70),
            disc=DISC(D=80, I=40),
        ),
    )
    result = compute_deviations(profile)
    assert result["mmpi"]["Hs"]["t"] == 70
    assert "pct" in result["mmpi"]["Hs"]
    assert result["big_five"]["openness"]["basis"] == "raw_range_only"
    assert "pct" not in result["big_five"]["openness"]
    assert result["disc"]["D"]["basis"] == "no_population_norm"
    assert "pct" not in result["disc"]["D"]


def test_markdown_warns_about_corporate_percentages():
    profile = ParsedProfile(employee=EmployeeInfo(), methods=MethodScores(mmpi=MMPI(D=60)))
    markdown = format_deviations_md(compute_deviations(profile))
    assert "Корпоративные проценты не являются популяционными перцентилями" in markdown
    assert '"D"' in markdown
