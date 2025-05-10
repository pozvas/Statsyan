from django import forms


class DemoUploadForm(forms.Form):
    file = forms.FileField(
        label="Выберите .dem файл",
        widget=forms.FileInput(attrs={"accept": ".dem"}),
    )
    file_mtime = forms.CharField(widget=forms.HiddenInput(), required=False)

    def clean_file(self):
        demo_file = self.data.get("file")
        if demo_file:
            if not demo_file.name.endswith(".dem"):
                raise forms.ValidationError(
                    "Разрешены только файлы с расширением .dem"
                )
        return demo_file
