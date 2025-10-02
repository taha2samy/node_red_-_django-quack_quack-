
from django.shortcuts import render,HttpResponse
from .models import Device,Element,ElementDetailsStyle
import logging

logger = logging.getLogger(__name__)

def test_view(request):
    return render(request,'test.html')
def tester_view(request):
    def get_element_with_details(element_id):
        element = Element.objects.get(id=element_id)
        details = ElementDetailsStyle.objects.filter(element=element)
        return [
            {**element.__dict__, "details": details[0].details},
            {**element.__dict__, "details": details[1].details},
        ]

    guage1, guage2 = get_element_with_details("98994c94-71b8-53b0-85f3-d1c6483978de")
    chart1, chart2 = get_element_with_details("9bd05e33-0ce7-5a76-9ae1-36ac067b3545")
    switch1, switch2 = get_element_with_details("e5b1cb93-114e-5609-9dcf-2b7360375e5a")
    slider1, slider2 = get_element_with_details("f53b2639-b17e-5604-8767-17254ebaa351")

    return render(
        request,
        r'cards/templates/test_guage.html',
        {'elements': [guage1, guage2, chart1, chart2, switch1, switch2, slider1, slider2]}
    )
