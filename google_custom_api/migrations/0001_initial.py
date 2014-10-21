# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'QueryEvent'
        db.create_table(u'google_custom_api_queryevent', (
            (u'queryevent_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['dolon.QueryEvent'], unique=True, primary_key=True)),
            ('c2coff', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('cr', self.gf('django.db.models.fields.CharField')(max_length=9, null=True, blank=True)),
            ('cref', self.gf('django.db.models.fields.URLField')(max_length=255, null=True, blank=True)),
            ('cx', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('dateRestrict_value', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('dateRestrict_by', self.gf('django.db.models.fields.CharField')(max_length=1, null=True, blank=True)),
            ('exactTerms', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='google_exactTerms', null=True, to=orm['dolon.QueryString'])),
            ('fileType', self.gf('django.db.models.fields.CharField')(max_length=10, null=True, blank=True)),
            ('filter', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('gl', self.gf('django.db.models.fields.CharField')(max_length=2, null=True, blank=True)),
            ('googlehost', self.gf('django.db.models.fields.CharField')(max_length=12, null=True, blank=True)),
            ('highRange', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('hl', self.gf('django.db.models.fields.CharField')(max_length=2, null=True, blank=True)),
            ('imgColorType', self.gf('django.db.models.fields.CharField')(max_length=5, null=True, blank=True)),
            ('imgDominantColor', self.gf('django.db.models.fields.CharField')(max_length=6, null=True, blank=True)),
            ('imgSize', self.gf('django.db.models.fields.CharField')(max_length=7, null=True, blank=True)),
            ('imgType', self.gf('django.db.models.fields.CharField')(max_length=7, null=True, blank=True)),
            ('linkSite', self.gf('django.db.models.fields.URLField')(max_length=255, null=True, blank=True)),
            ('lowRange', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('lr', self.gf('django.db.models.fields.CharField')(max_length=10, null=True, blank=True)),
            ('num', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('relatedSite', self.gf('django.db.models.fields.URLField')(max_length=255, null=True, blank=True)),
            ('rights', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('safe', self.gf('django.db.models.fields.CharField')(default='off', max_length=6)),
            ('searchType', self.gf('django.db.models.fields.CharField')(default='image', max_length=5)),
            ('siteSearch', self.gf('django.db.models.fields.URLField')(max_length=255, null=True, blank=True)),
            ('siteSearchFilter', self.gf('django.db.models.fields.CharField')(max_length=1, null=True, blank=True)),
            ('sort', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('start', self.gf('django.db.models.fields.IntegerField')(default=1)),
        ))
        db.send_create_signal(u'google_custom_api', ['QueryEvent'])

        # Adding M2M table for field excludeTerms on 'QueryEvent'
        m2m_table_name = db.shorten_name(u'google_custom_api_queryevent_excludeTerms')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('queryevent', models.ForeignKey(orm[u'google_custom_api.queryevent'], null=False)),
            ('querystring', models.ForeignKey(orm[u'dolon.querystring'], null=False))
        ))
        db.create_unique(m2m_table_name, ['queryevent_id', 'querystring_id'])

        # Adding M2M table for field hq on 'QueryEvent'
        m2m_table_name = db.shorten_name(u'google_custom_api_queryevent_hq')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('queryevent', models.ForeignKey(orm[u'google_custom_api.queryevent'], null=False)),
            ('querystring', models.ForeignKey(orm[u'dolon.querystring'], null=False))
        ))
        db.create_unique(m2m_table_name, ['queryevent_id', 'querystring_id'])

        # Adding M2M table for field orTerms on 'QueryEvent'
        m2m_table_name = db.shorten_name(u'google_custom_api_queryevent_orTerms')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('queryevent', models.ForeignKey(orm[u'google_custom_api.queryevent'], null=False)),
            ('querystring', models.ForeignKey(orm[u'dolon.querystring'], null=False))
        ))
        db.create_unique(m2m_table_name, ['queryevent_id', 'querystring_id'])


    def backwards(self, orm):
        # Deleting model 'QueryEvent'
        db.delete_table(u'google_custom_api_queryevent')

        # Removing M2M table for field excludeTerms on 'QueryEvent'
        db.delete_table(db.shorten_name(u'google_custom_api_queryevent_excludeTerms'))

        # Removing M2M table for field hq on 'QueryEvent'
        db.delete_table(db.shorten_name(u'google_custom_api_queryevent_hq'))

        # Removing M2M table for field orTerms on 'QueryEvent'
        db.delete_table(db.shorten_name(u'google_custom_api_queryevent_orTerms'))


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'dolon.context': {
            'Meta': {'object_name': 'Context'},
            'author': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'content': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'diffbot_requests': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'requesting_context'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['dolon.DiffBotRequest']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'publicationDate': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'retrieved': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'tagged_contexts'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['dolon.Tag']"}),
            'text_content': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '400', 'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '2000'}),
            'use_diffbot': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        u'dolon.diffbotrequest': {
            'Meta': {'object_name': 'DiffBotRequest'},
            'attempted': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'completed': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'parameters': ('dolon.models.ListField', [], {'default': "['']"}),
            'response': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'dolon.engine': {
            'Meta': {'object_name': 'Engine'},
            'daylimit': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'dayusage': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'manager': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'monthlimit': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'monthusage': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'oauth_token': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['dolon.OAuthAccessToken']", 'null': 'True', 'blank': 'True'}),
            'pagelimit': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'pagesize': ('django.db.models.fields.IntegerField', [], {'default': '10'}),
            'parameters': ('dolon.models.ListField', [], {}),
            'ratelimit': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'dolon.grouptask': {
            'Meta': {'object_name': 'GroupTask'},
            'dispatched': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'subtask_ids': ('dolon.models.ListField', [], {}),
            'task_id': ('django.db.models.fields.CharField', [], {'max_length': '1000'})
        },
        u'dolon.hashtag': {
            'Meta': {'object_name': 'HashTag'},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'string': ('django.db.models.fields.CharField', [], {'max_length': '500'})
        },
        u'dolon.item': {
            'Meta': {'object_name': 'Item'},
            'context': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'items'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['dolon.Context']"}),
            'creationDate': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.CharField', [], {'max_length': '400', 'null': 'True', 'blank': 'True'}),
            'events': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'items'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['dolon.QueryEvent']"}),
            'hide': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'merged_with': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'merged_from'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': u"orm['dolon.Item']"}),
            'retrieved': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'PG'", 'max_length': '2'}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'tagged_items'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['dolon.Tag']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '400', 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '2000'})
        },
        u'dolon.oauthaccesstoken': {
            'Meta': {'object_name': 'OAuthAccessToken'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'expires': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'oauth_access_token': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'oauth_access_token_secret': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'oauth_token': ('django.db.models.fields.CharField', [], {'max_length': '1000'}),
            'oauth_token_secret': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'oauth_verifier': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'null': 'True', 'blank': 'True'}),
            'platform': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['dolon.SocialPlatform']", 'null': 'True', 'blank': 'True'}),
            'screen_name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'user_id': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'})
        },
        u'dolon.queryevent': {
            'Meta': {'object_name': 'QueryEvent'},
            'after': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'before': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'created_events'", 'null': 'True', 'to': u"orm['auth.User']"}),
            'datetime': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'dispatched': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'engine': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'engine_events'", 'to': u"orm['dolon.Engine']"}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'queryresults': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'event_instance'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['dolon.QueryResult']"}),
            'querystring': ('django.db.models.fields.related.ForeignKey', [], {'default': '-1', 'related_name': "'queryevents'", 'null': 'True', 'blank': 'True', 'to': u"orm['dolon.QueryString']"}),
            'rangeEnd': ('django.db.models.fields.IntegerField', [], {'default': '10', 'null': 'True', 'blank': 'True'}),
            'rangeStart': ('django.db.models.fields.IntegerField', [], {'default': '1', 'null': 'True', 'blank': 'True'}),
            'search_by': ('django.db.models.fields.CharField', [], {'default': "'ST'", 'max_length': '2'}),
            'search_task': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'searchtaskevent'", 'null': 'True', 'to': u"orm['dolon.GroupTask']"}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['dolon.HashTag']", 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['dolon.SocialUser']", 'null': 'True', 'blank': 'True'})
        },
        u'dolon.queryresult': {
            'Meta': {'object_name': 'QueryResult'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rangeEnd': ('django.db.models.fields.IntegerField', [], {}),
            'rangeStart': ('django.db.models.fields.IntegerField', [], {}),
            'result': ('django.db.models.fields.TextField', [], {}),
            'resultitems': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'queryresult_instance'", 'symmetrical': 'False', 'to': u"orm['dolon.QueryResultItem']"})
        },
        u'dolon.queryresultitem': {
            'Meta': {'object_name': 'QueryResultItem'},
            'contextURL': ('django.db.models.fields.URLField', [], {'max_length': '2000'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'query_result_item'", 'null': 'True', 'to': u"orm['dolon.Item']"}),
            'params': ('django.db.models.fields.CharField', [], {'max_length': '50000', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '400', 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '2000'})
        },
        u'dolon.querystring': {
            'Meta': {'object_name': 'QueryString'},
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'querystring': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '1000'})
        },
        u'dolon.socialplatform': {
            'Meta': {'object_name': 'SocialPlatform'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '500'})
        },
        u'dolon.socialuser': {
            'Meta': {'object_name': 'SocialUser'},
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'handle': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'platform': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['dolon.SocialPlatform']"}),
            'profile_url': ('django.db.models.fields.CharField', [], {'max_length': '500', 'null': 'True', 'blank': 'True'}),
            'user_id': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'})
        },
        u'dolon.tag': {
            'Meta': {'object_name': 'Tag'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'text': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200'})
        },
        u'google_custom_api.queryevent': {
            'Meta': {'object_name': 'QueryEvent', '_ormbases': [u'dolon.QueryEvent']},
            'c2coff': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'cr': ('django.db.models.fields.CharField', [], {'max_length': '9', 'null': 'True', 'blank': 'True'}),
            'cref': ('django.db.models.fields.URLField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'cx': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'dateRestrict_by': ('django.db.models.fields.CharField', [], {'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'dateRestrict_value': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'exactTerms': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'google_exactTerms'", 'null': 'True', 'to': u"orm['dolon.QueryString']"}),
            'excludeTerms': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'google_excludeTerms'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['dolon.QueryString']"}),
            'fileType': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'filter': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'gl': ('django.db.models.fields.CharField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'googlehost': ('django.db.models.fields.CharField', [], {'max_length': '12', 'null': 'True', 'blank': 'True'}),
            'highRange': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'hl': ('django.db.models.fields.CharField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'hq': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['dolon.QueryString']", 'null': 'True', 'blank': 'True'}),
            'imgColorType': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            'imgDominantColor': ('django.db.models.fields.CharField', [], {'max_length': '6', 'null': 'True', 'blank': 'True'}),
            'imgSize': ('django.db.models.fields.CharField', [], {'max_length': '7', 'null': 'True', 'blank': 'True'}),
            'imgType': ('django.db.models.fields.CharField', [], {'max_length': '7', 'null': 'True', 'blank': 'True'}),
            'linkSite': ('django.db.models.fields.URLField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'lowRange': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'lr': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'num': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'orTerms': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'google_orTerms'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['dolon.QueryString']"}),
            u'queryevent_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['dolon.QueryEvent']", 'unique': 'True', 'primary_key': 'True'}),
            'relatedSite': ('django.db.models.fields.URLField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'rights': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'safe': ('django.db.models.fields.CharField', [], {'default': "'off'", 'max_length': '6'}),
            'searchType': ('django.db.models.fields.CharField', [], {'default': "'image'", 'max_length': '5'}),
            'siteSearch': ('django.db.models.fields.URLField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'siteSearchFilter': ('django.db.models.fields.CharField', [], {'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'sort': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'start': ('django.db.models.fields.IntegerField', [], {'default': '1'})
        }
    }

    complete_apps = ['google_custom_api']