from django import forms

from apps.eventos.repositorio import CATEGORIAS, STATUS


class EventoForm(forms.Form):
    nome = forms.CharField(max_length=80, widget=forms.TextInput(attrs={"placeholder": "Ex.: Festival de Inverno"}))
    descricao = forms.CharField(label="Descrição", max_length=400, widget=forms.Textarea(attrs={"rows": 3}))
    categoria = forms.ChoiceField(choices=CATEGORIAS.items())
    status = forms.ChoiceField(
        choices=[(k, v) for k, v in STATUS.items() if k != "realizado"],
        initial="proposta",
        help_text="\"Em validação\" publica a ideia para medir a demanda antes de investir.",
    )
    data = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    horario = forms.TimeField(label="Horário", widget=forms.TimeInput(attrs={"type": "time"}))
    local = forms.CharField(max_length=80, widget=forms.TextInput(attrs={"placeholder": "Ex.: Hall Central · Piso L1"}))
    investimento_estimado = forms.IntegerField(label="Investimento estimado (R$)", min_value=0, required=False)
    informacoes = forms.CharField(label="Informações adicionais", max_length=200, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            classe = "form-select" if isinstance(campo, forms.ChoiceField) else "form-control"
            campo.widget.attrs.setdefault("class", classe)

    def para_evento(self):
        d = self.cleaned_data
        return {
            "nome": d["nome"], "descricao": d["descricao"], "categoria": d["categoria"],
            "status": d["status"], "data": d["data"].isoformat(), "horario": d["horario"].strftime("%H:%M"),
            "local": d["local"], "investimento_estimado": d["investimento_estimado"] or 0,
            "informacoes": d["informacoes"],
        }
