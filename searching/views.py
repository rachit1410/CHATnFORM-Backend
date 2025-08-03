from rest_framework.views import APIView
from searching.documents import UserDocument
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated


class SearchUserAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.GET.get("q")
        data = []
        s = UserDocument.search().filter("match", name=query)

        for hit in s:
            if not hit.id == request.user.pk:
                data.append({
                    'id': hit.id,
                    'name': hit.name
                })

        return Response(
            {
                'status': True,
                'message': 'Info: Search results fetched.',
                'data': data
            }
        )
