
# Create your views here.
from django.shortcuts import render,HttpResponse
from .models import Device,Element,ElementDetailsStyle
def test_view(request):
    return render(request,'test.html')
def tester_view(request):
    
    guage = Element.objects.get(id="98994c94-71b8-53b0-85f3-d1c6483978de")
    guage1= (guage)
    guage2= (guage)
    guage1.details=ElementDetailsStyle.objects.filter(element=guage).first().details
    guage2.details=ElementDetailsStyle.objects.filter(element=guage)[1].details
    chart= Element.objects.get(id="9bd05e33-0ce7-5a76-9ae1-36ac067b3545")
    chart1= (chart)
    chart2= (chart)
    chart1.details=ElementDetailsStyle.objects.filter(element=chart).first().details
    chart2.details=ElementDetailsStyle.objects.filter(element=chart)[1].details
    switch= Element.objects.get(id="e5b1cb93-114e-5609-9dcf-2b7360375e5a")
    switch1= (switch)
    switch2= (switch)
    switch1.details=ElementDetailsStyle.objects.filter(element=switch).first().details
    switch2.details=ElementDetailsStyle.objects.filter(element=switch)[1].details
    return render(request,r'cards/templates/test_guage.html',{'elements':[guage1,guage2,chart1,chart2,switch1,switch2]})