import datetime
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, render_to_response, redirect
from django.http import HttpResponse
from django.contrib.comments.models import Comment
from django.contrib.contenttypes.models import ContentType
from django.views.generic import list_detail
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.conf import settings
from brainstorm.models import Subsite, Idea, Vote

def idea_list(request, slug, ordering='-total_upvotes'):
    subsite = get_object_or_404(Subsite, pk=slug)

    ordering_db = {'most_popular': '-score',
                   'latest': '-submit_date'}[ordering]
    qs = Idea.objects.with_user_vote(request.user).filter(subsite=subsite).select_related().order_by(ordering_db)
    if hasattr(qs, '_gatekeeper'):
        qs = qs.approved()
    return list_detail.object_list(request, queryset=qs,
        extra_context={'ordering': ordering, 'subsite': subsite,
                       'user_can_post': subsite.user_can_post(request.user)},
        paginate_by=10,
        template_object_name='idea')

def idea_detail(request, slug, id):
    subsite = get_object_or_404(Subsite, pk=slug)

    idea = get_object_or_404(Idea.objects.with_user_vote(request.user).filter(subsite=subsite), pk=id)
    return render_to_response('brainstorm/idea_detail.html',
                              {'idea': idea, 'subsite': subsite,
                               'user_can_post': subsite.user_can_post(request.user)},
                              context_instance=RequestContext(request))

@require_POST
def new_idea(request, slug):
    subsite = get_object_or_404(Subsite, pk=slug)
    if not subsite.user_can_post(request.user):
        return redirect(subsite.get_absolute_url())
    title = request.POST['title']
    description = request.POST['description']
    if not title.strip() or not description.strip():
        return redirect(subsite.get_absolute_url())
    user = request.user
    idea = Idea.objects.create(title=title, description=description, user=user,
                               subsite=subsite)
    return redirect(idea)

@require_POST
@login_required
def vote(request):
    idea_id = int(request.POST.get('idea'))
    score = int(request.POST.get('score'))
    if score not in (0,1):
        score = 0
    idea = get_object_or_404(Idea, pk=idea_id)
    score_diff = score
    vote, created = Vote.objects.get_or_create(user=request.user, idea=idea,
                                               defaults={'value':score})
    if not created:
        new_score = idea.score + (score-vote.value)
        vote.value = score
        vote.save()
    else:
        new_score = idea.score

    if request.is_ajax():
        return HttpResponse("{'score':%d}" % new_score)

    return redirect(idea)
