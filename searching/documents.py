from django_elasticsearch_dsl import Document
from django_elasticsearch_dsl.registries import registry
from django.contrib.auth import get_user_model


@registry.register_document
class UserDocument(Document):
    class Index:
        # Name of the Elasticsearch index
        name = 'users'
        # See Elasticsearch Indices API reference for available settings
        settings = {'number_of_shards': 1,
                    'number_of_replicas': 0}

    class Django:
        User = get_user_model()
        model = User

        fields = [
            'id',
            'name'
        ]
