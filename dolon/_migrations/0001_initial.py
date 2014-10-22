# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'QueryString'
        db.create_table(u'dolon_querystring', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('querystring', self.gf('django.db.models.fields.CharField')(unique=True, max_length=1000)),
        ))
        db.send_create_signal(u'dolon', ['QueryString'])

        # Adding model 'Engine'
        db.create_table(u'dolon_engine', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('parameters', self.gf('dolon.models.ListField')()),
            ('manager', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('ratelimit', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('daylimit', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('dayusage', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('monthlimit', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('monthusage', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('pagesize', self.gf('django.db.models.fields.IntegerField')(default=10)),
            ('pagelimit', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'dolon', ['Engine'])

        # Adding model 'QueryEvent'
        db.create_table(u'dolon_queryevent', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('querystring', self.gf('django.db.models.fields.related.ForeignKey')(related_name='queryevents', to=orm['dolon.QueryString'])),
            ('rangeStart', self.gf('django.db.models.fields.IntegerField')()),
            ('rangeEnd', self.gf('django.db.models.fields.IntegerField')()),
            ('datetime', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('dispatched', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('state', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True)),
            ('search_task', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='searchtaskevent', null=True, to=orm['dolon.GroupTask'])),
            ('creator', self.gf('django.db.models.fields.related.ForeignKey')(related_name='created_events', blank=True, to=orm['auth.User'])),
            ('engine', self.gf('django.db.models.fields.related.ForeignKey')(related_name='engine_events', to=orm['dolon.Engine'])),
        ))
        db.send_create_signal(u'dolon', ['QueryEvent'])

        # Adding M2M table for field thumbnail_tasks on 'QueryEvent'
        m2m_table_name = db.shorten_name(u'dolon_queryevent_thumbnail_tasks')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('queryevent', models.ForeignKey(orm[u'dolon.queryevent'], null=False)),
            ('grouptask', models.ForeignKey(orm[u'dolon.grouptask'], null=False))
        ))
        db.create_unique(m2m_table_name, ['queryevent_id', 'grouptask_id'])

        # Adding M2M table for field queryresults on 'QueryEvent'
        m2m_table_name = db.shorten_name(u'dolon_queryevent_queryresults')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('queryevent', models.ForeignKey(orm[u'dolon.queryevent'], null=False)),
            ('queryresult', models.ForeignKey(orm[u'dolon.queryresult'], null=False))
        ))
        db.create_unique(m2m_table_name, ['queryevent_id', 'queryresult_id'])

        # Adding model 'QueryResult'
        db.create_table(u'dolon_queryresult', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('rangeStart', self.gf('django.db.models.fields.IntegerField')()),
            ('rangeEnd', self.gf('django.db.models.fields.IntegerField')()),
            ('result', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal(u'dolon', ['QueryResult'])

        # Adding M2M table for field resultitems on 'QueryResult'
        m2m_table_name = db.shorten_name(u'dolon_queryresult_resultitems')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('queryresult', models.ForeignKey(orm[u'dolon.queryresult'], null=False)),
            ('queryresultitem', models.ForeignKey(orm[u'dolon.queryresultitem'], null=False))
        ))
        db.create_unique(m2m_table_name, ['queryresult_id', 'queryresultitem_id'])

        # Adding model 'QueryResultItem'
        db.create_table(u'dolon_queryresultitem', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=2000)),
            ('contextURL', self.gf('django.db.models.fields.URLField')(max_length=2000)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=400, null=True, blank=True)),
            ('params', self.gf('django.db.models.fields.CharField')(max_length=50000, null=True, blank=True)),
            ('item', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='query_result_item', null=True, to=orm['dolon.Item'])),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=50)),
        ))
        db.send_create_signal(u'dolon', ['QueryResultItem'])

        # Adding model 'Item'
        db.create_table(u'dolon_item', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('url', self.gf('django.db.models.fields.URLField')(unique=True, max_length=2000)),
            ('status', self.gf('django.db.models.fields.CharField')(default='PG', max_length=2)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=400, null=True, blank=True)),
            ('creator', self.gf('django.db.models.fields.CharField')(max_length=400, null=True, blank=True)),
            ('creationDate', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('merged_with', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='merged_from', null=True, on_delete=models.SET_NULL, to=orm['dolon.Item'])),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True)),
            ('hide', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('retrieved', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'dolon', ['Item'])

        # Adding M2M table for field context on 'Item'
        m2m_table_name = db.shorten_name(u'dolon_item_context')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('item', models.ForeignKey(orm[u'dolon.item'], null=False)),
            ('context', models.ForeignKey(orm[u'dolon.context'], null=False))
        ))
        db.create_unique(m2m_table_name, ['item_id', 'context_id'])

        # Adding M2M table for field events on 'Item'
        m2m_table_name = db.shorten_name(u'dolon_item_events')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('item', models.ForeignKey(orm[u'dolon.item'], null=False)),
            ('queryevent', models.ForeignKey(orm[u'dolon.queryevent'], null=False))
        ))
        db.create_unique(m2m_table_name, ['item_id', 'queryevent_id'])

        # Adding M2M table for field tags on 'Item'
        m2m_table_name = db.shorten_name(u'dolon_item_tags')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('item', models.ForeignKey(orm[u'dolon.item'], null=False)),
            ('tag', models.ForeignKey(orm[u'dolon.tag'], null=False))
        ))
        db.create_unique(m2m_table_name, ['item_id', 'tag_id'])

        # Adding model 'ImageItem'
        db.create_table(u'dolon_imageitem', (
            (u'item_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['dolon.Item'], unique=True, primary_key=True)),
            ('height', self.gf('django.db.models.fields.IntegerField')(default=0, null=True, blank=True)),
            ('width', self.gf('django.db.models.fields.IntegerField')(default=0, null=True, blank=True)),
            ('thumbnail', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='imageitem_thumbnail', null=True, to=orm['dolon.Thumbnail'])),
            ('image', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='imageitem_fullsize', null=True, to=orm['dolon.Image'])),
        ))
        db.send_create_signal(u'dolon', ['ImageItem'])

        # Adding model 'VideoItem'
        db.create_table(u'dolon_videoitem', (
            (u'item_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['dolon.Item'], unique=True, primary_key=True)),
            ('length', self.gf('django.db.models.fields.IntegerField')(default=0, null=True, blank=True)),
        ))
        db.send_create_signal(u'dolon', ['VideoItem'])

        # Adding M2M table for field thumbnails on 'VideoItem'
        m2m_table_name = db.shorten_name(u'dolon_videoitem_thumbnails')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('videoitem', models.ForeignKey(orm[u'dolon.videoitem'], null=False)),
            ('thumbnail', models.ForeignKey(orm[u'dolon.thumbnail'], null=False))
        ))
        db.create_unique(m2m_table_name, ['videoitem_id', 'thumbnail_id'])

        # Adding M2M table for field videos on 'VideoItem'
        m2m_table_name = db.shorten_name(u'dolon_videoitem_videos')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('videoitem', models.ForeignKey(orm[u'dolon.videoitem'], null=False)),
            ('video', models.ForeignKey(orm[u'dolon.video'], null=False))
        ))
        db.create_unique(m2m_table_name, ['videoitem_id', 'video_id'])

        # Adding model 'AudioItem'
        db.create_table(u'dolon_audioitem', (
            (u'item_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['dolon.Item'], unique=True, primary_key=True)),
            ('thumbnail', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='audioitem_thumbnail', null=True, to=orm['dolon.Thumbnail'])),
            ('length', self.gf('django.db.models.fields.IntegerField')(default=0, null=True, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'dolon', ['AudioItem'])

        # Adding M2M table for field audio_segments on 'AudioItem'
        m2m_table_name = db.shorten_name(u'dolon_audioitem_audio_segments')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('audioitem', models.ForeignKey(orm[u'dolon.audioitem'], null=False)),
            ('audio', models.ForeignKey(orm[u'dolon.audio'], null=False))
        ))
        db.create_unique(m2m_table_name, ['audioitem_id', 'audio_id'])

        # Adding model 'TextItem'
        db.create_table(u'dolon_textitem', (
            (u'item_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['dolon.Item'], unique=True, primary_key=True)),
            ('snippet', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('length', self.gf('django.db.models.fields.IntegerField')(default=0, null=True, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('contents', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'dolon', ['TextItem'])

        # Adding M2M table for field original_files on 'TextItem'
        m2m_table_name = db.shorten_name(u'dolon_textitem_original_files')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('textitem', models.ForeignKey(orm[u'dolon.textitem'], null=False)),
            ('text', models.ForeignKey(orm[u'dolon.text'], null=False))
        ))
        db.create_unique(m2m_table_name, ['textitem_id', 'text_id'])

        # Adding model 'GroupTask'
        db.create_table(u'dolon_grouptask', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('task_id', self.gf('django.db.models.fields.CharField')(max_length=1000)),
            ('subtask_ids', self.gf('dolon.models.ListField')()),
            ('dispatched', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal(u'dolon', ['GroupTask'])

        # Adding model 'Thumbnail'
        db.create_table(u'dolon_thumbnail', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('url', self.gf('django.db.models.fields.URLField')(unique=True, max_length=2000)),
            ('image', self.gf('django.db.models.fields.files.ImageField')(max_length=100, null=True, blank=True)),
            ('mime', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True)),
            ('height', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('width', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal(u'dolon', ['Thumbnail'])

        # Adding model 'Text'
        db.create_table(u'dolon_text', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('url', self.gf('django.db.models.fields.URLField')(unique=True, max_length=2000)),
            ('text_file', self.gf('django.db.models.fields.files.FileField')(max_length=100, null=True, blank=True)),
            ('size', self.gf('django.db.models.fields.IntegerField')(default=0, null=True, blank=True)),
            ('mime', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True)),
        ))
        db.send_create_signal(u'dolon', ['Text'])

        # Adding model 'Image'
        db.create_table(u'dolon_image', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('url', self.gf('django.db.models.fields.URLField')(unique=True, max_length=2000)),
            ('image', self.gf('django.db.models.fields.files.ImageField')(max_length=100, null=True, blank=True)),
            ('size', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('mime', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True)),
            ('height', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('width', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal(u'dolon', ['Image'])

        # Adding model 'Video'
        db.create_table(u'dolon_video', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('url', self.gf('django.db.models.fields.URLField')(unique=True, max_length=2000)),
            ('video', self.gf('django.db.models.fields.files.FileField')(max_length=100, null=True, blank=True)),
            ('size', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('length', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('mime', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True)),
        ))
        db.send_create_signal(u'dolon', ['Video'])

        # Adding model 'Audio'
        db.create_table(u'dolon_audio', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('url', self.gf('django.db.models.fields.URLField')(unique=True, max_length=2000)),
            ('size', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('length', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('mime', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True)),
            ('audio_file', self.gf('django.db.models.fields.files.FileField')(max_length=100, null=True, blank=True)),
        ))
        db.send_create_signal(u'dolon', ['Audio'])

        # Adding model 'Tag'
        db.create_table(u'dolon_tag', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('text', self.gf('django.db.models.fields.CharField')(unique=True, max_length=200)),
        ))
        db.send_create_signal(u'dolon', ['Tag'])

        # Adding model 'Context'
        db.create_table(u'dolon_context', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('url', self.gf('django.db.models.fields.URLField')(unique=True, max_length=2000)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=400, null=True, blank=True)),
            ('content', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('publicationDate', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'dolon', ['Context'])

        # Adding M2M table for field tags on 'Context'
        m2m_table_name = db.shorten_name(u'dolon_context_tags')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('context', models.ForeignKey(orm[u'dolon.context'], null=False)),
            ('tag', models.ForeignKey(orm[u'dolon.tag'], null=False))
        ))
        db.create_unique(m2m_table_name, ['context_id', 'tag_id'])


    def backwards(self, orm):
        # Deleting model 'QueryString'
        db.delete_table(u'dolon_querystring')

        # Deleting model 'Engine'
        db.delete_table(u'dolon_engine')

        # Deleting model 'QueryEvent'
        db.delete_table(u'dolon_queryevent')

        # Removing M2M table for field thumbnail_tasks on 'QueryEvent'
        db.delete_table(db.shorten_name(u'dolon_queryevent_thumbnail_tasks'))

        # Removing M2M table for field queryresults on 'QueryEvent'
        db.delete_table(db.shorten_name(u'dolon_queryevent_queryresults'))

        # Deleting model 'QueryResult'
        db.delete_table(u'dolon_queryresult')

        # Removing M2M table for field resultitems on 'QueryResult'
        db.delete_table(db.shorten_name(u'dolon_queryresult_resultitems'))

        # Deleting model 'QueryResultItem'
        db.delete_table(u'dolon_queryresultitem')

        # Deleting model 'Item'
        db.delete_table(u'dolon_item')

        # Removing M2M table for field context on 'Item'
        db.delete_table(db.shorten_name(u'dolon_item_context'))

        # Removing M2M table for field events on 'Item'
        db.delete_table(db.shorten_name(u'dolon_item_events'))

        # Removing M2M table for field tags on 'Item'
        db.delete_table(db.shorten_name(u'dolon_item_tags'))

        # Deleting model 'ImageItem'
        db.delete_table(u'dolon_imageitem')

        # Deleting model 'VideoItem'
        db.delete_table(u'dolon_videoitem')

        # Removing M2M table for field thumbnails on 'VideoItem'
        db.delete_table(db.shorten_name(u'dolon_videoitem_thumbnails'))

        # Removing M2M table for field videos on 'VideoItem'
        db.delete_table(db.shorten_name(u'dolon_videoitem_videos'))

        # Deleting model 'AudioItem'
        db.delete_table(u'dolon_audioitem')

        # Removing M2M table for field audio_segments on 'AudioItem'
        db.delete_table(db.shorten_name(u'dolon_audioitem_audio_segments'))

        # Deleting model 'TextItem'
        db.delete_table(u'dolon_textitem')

        # Removing M2M table for field original_files on 'TextItem'
        db.delete_table(db.shorten_name(u'dolon_textitem_original_files'))

        # Deleting model 'GroupTask'
        db.delete_table(u'dolon_grouptask')

        # Deleting model 'Thumbnail'
        db.delete_table(u'dolon_thumbnail')

        # Deleting model 'Text'
        db.delete_table(u'dolon_text')

        # Deleting model 'Image'
        db.delete_table(u'dolon_image')

        # Deleting model 'Video'
        db.delete_table(u'dolon_video')

        # Deleting model 'Audio'
        db.delete_table(u'dolon_audio')

        # Deleting model 'Tag'
        db.delete_table(u'dolon_tag')

        # Deleting model 'Context'
        db.delete_table(u'dolon_context')

        # Removing M2M table for field tags on 'Context'
        db.delete_table(db.shorten_name(u'dolon_context_tags'))


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
        u'dolon.audio': {
            'Meta': {'object_name': 'Audio'},
            'audio_file': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'length': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'mime': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'size': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '2000'})
        },
        u'dolon.audioitem': {
            'Meta': {'object_name': 'AudioItem', '_ormbases': [u'dolon.Item']},
            'audio_segments': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'segment'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['dolon.Audio']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'item_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['dolon.Item']", 'unique': 'True', 'primary_key': 'True'}),
            'length': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'thumbnail': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'audioitem_thumbnail'", 'null': 'True', 'to': u"orm['dolon.Thumbnail']"})
        },
        u'dolon.context': {
            'Meta': {'object_name': 'Context'},
            'content': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'publicationDate': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'tagged_contexts'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['dolon.Tag']"}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '400', 'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '2000'})
        },
        u'dolon.engine': {
            'Meta': {'object_name': 'Engine'},
            'daylimit': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'dayusage': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'manager': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'monthlimit': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'monthusage': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
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
        u'dolon.image': {
            'Meta': {'object_name': 'Image'},
            'height': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'mime': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'size': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '2000'}),
            'width': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        u'dolon.imageitem': {
            'Meta': {'object_name': 'ImageItem', '_ormbases': [u'dolon.Item']},
            'height': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'imageitem_fullsize'", 'null': 'True', 'to': u"orm['dolon.Image']"}),
            u'item_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['dolon.Item']", 'unique': 'True', 'primary_key': 'True'}),
            'thumbnail': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'imageitem_thumbnail'", 'null': 'True', 'to': u"orm['dolon.Thumbnail']"}),
            'width': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'})
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
        u'dolon.queryevent': {
            'Meta': {'object_name': 'QueryEvent'},
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'created_events'", 'blank': 'True', 'to': u"orm['auth.User']"}),
            'datetime': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'dispatched': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'engine': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'engine_events'", 'to': u"orm['dolon.Engine']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'queryresults': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'event_instance'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['dolon.QueryResult']"}),
            'querystring': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'queryevents'", 'to': u"orm['dolon.QueryString']"}),
            'rangeEnd': ('django.db.models.fields.IntegerField', [], {}),
            'rangeStart': ('django.db.models.fields.IntegerField', [], {}),
            'search_task': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'searchtaskevent'", 'null': 'True', 'to': u"orm['dolon.GroupTask']"}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'thumbnail_tasks': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'thumbtaskevent'", 'symmetrical': 'False', 'to': u"orm['dolon.GroupTask']"})
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
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'querystring': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '1000'})
        },
        u'dolon.tag': {
            'Meta': {'object_name': 'Tag'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'text': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200'})
        },
        u'dolon.text': {
            'Meta': {'object_name': 'Text'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mime': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'size': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'text_file': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '2000'})
        },
        u'dolon.textitem': {
            'Meta': {'object_name': 'TextItem', '_ormbases': [u'dolon.Item']},
            'contents': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'item_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['dolon.Item']", 'unique': 'True', 'primary_key': 'True'}),
            'length': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'original_files': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['dolon.Text']", 'null': 'True', 'blank': 'True'}),
            'snippet': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        u'dolon.thumbnail': {
            'Meta': {'object_name': 'Thumbnail'},
            'height': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'mime': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '2000'}),
            'width': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        u'dolon.video': {
            'Meta': {'object_name': 'Video'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'length': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'mime': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'size': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'url': ('django.db.models.fields.URLField', [], {'unique': 'True', 'max_length': '2000'}),
            'video': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'})
        },
        u'dolon.videoitem': {
            'Meta': {'object_name': 'VideoItem', '_ormbases': [u'dolon.Item']},
            u'item_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['dolon.Item']", 'unique': 'True', 'primary_key': 'True'}),
            'length': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'thumbnails': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'video_items'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['dolon.Thumbnail']"}),
            'videos': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'videoitem'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['dolon.Video']"})
        }
    }

    complete_apps = ['dolon']