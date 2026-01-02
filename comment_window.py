import typing
import xbmc
import xbmcaddon
import xbmcgui
from xbmcgui import Dialog, ListItem, WindowXMLDialog

import bitchute_access

addon = xbmcaddon.Addon()
tr = addon.getLocalizedString

class CommentWindowXML(WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        WindowXMLDialog.__init__(self, *args, **kwargs)
        self.video_id = kwargs['video_id']
        self.last_selected_position = -1
        self.selected_comment_id = kwargs['selected_comment_id']

    def onInit(self):
        try:
            self.refresh()
        except Exception as e:
            raise e

    def onAction(self, action):
        try:
            self._onAction(action)
        except Exception as e:
            xbmc.log("Exception: " + str(e))

    def _onAction(self, action):
        if action == xbmcgui.ACTION_CONTEXT_MENU:
            ccl = self.get_comment_control_list()
            selected_pos = ccl.getSelectedPosition()
            item = ccl.getSelectedItem()

            menu = []
            offsets = []
            offset = 0
            invalid_offset = 10000

            id = item.getProperty('id')
            is_user = item.getProperty('is_user') == '1'

            if item and not is_user:
                if item.getProperty('user_vote') != str(0):
                    menu.append(tr(30040)) # Clear Vote
                    offsets.append(offset)
                    offset = offset + 1
                else:
                    offsets.append(invalid_offset)

                if item.getProperty('user_vote') != str(1):
                    menu.append(tr(30041)) # Like
                    offsets.append(offset)
                    offset = offset + 1
                else:
                    offsets.append(invalid_offset)

                if item.getProperty('user_vote') != str(-1):
                    menu.append(tr(30042)) # Dislike
                    offsets.append(offset)
                    offset = offset + 1
                else:
                    offsets.append(invalid_offset)
            else:
                offsets.append(invalid_offset)
                offsets.append(invalid_offset)
                offsets.append(invalid_offset)
                offset = 0

            menu.append(tr(30043)) # New comment
            offsets.append(offset)
            offset = offset + 1

            if item:
                menu.append(tr(30044)) # Reply
                offsets.append(offset)
                offset = offset + 1

                if is_user:
                    menu.append(tr(30045)) # Edit
                    offsets.append(offset)
                    offset = offset + 1

                    menu.append(tr(30046)) # Remove
                    offsets.append(offset)
                    offset = offset + 1
                else:
                    offsets.append(invalid_offset)
                    offsets.append(invalid_offset)
            else:
                offsets.append(invalid_offset)
                offsets.append(invalid_offset)
                offsets.append(invalid_offset)

            menu.append(tr(30047)) # Refresh
            offsets.append(offset)

            id = item.getProperty('id')
            parent_id = item.getProperty('parent_id')
            creator = item.getProperty('creator')
            fullname = item.getProperty('fullname')

            ret = Dialog().contextmenu(menu)

            if ret == offsets[0]: # Clear Vote
                self.neutral(id, parent_id, creator, fullname)

                if int(item.getProperty('user_vote')) == -1:
                    item.setProperty('downvote_count', str(int(item.getProperty('downvote_count'))-1))
                else:
                    item.setProperty('upvote_count', str(int(item.getProperty('upvote_count'))-1))

                item.setProperty('user_vote', str(0))
                self.refresh_label(item)

            elif ret == offsets[1]: # Like
                self.like(id, parent_id, creator, fullname)
                if int(item.getProperty('user_vote')) == -1:
                    item.setProperty('downvote_count', str(int(item.getProperty('downvote_count'))-1))
                item.setProperty('upvote_count', str(int(item.getProperty('upvote_count'))+1))
                item.setProperty('user_vote', str(1))
                self.refresh_label(item)

            elif ret == offsets[2]: # Dislike
                self.dislike(id, parent_id, creator, fullname)
                if int(item.getProperty('user_vote')) == 1:
                    item.setProperty('upvote_count', str(int(item.getProperty('upvote_count'))-1))
                item.setProperty('downvote_count', str(int(item.getProperty('downvote_count'))+1))
                item.setProperty('user_vote', str(-1))
                self.refresh_label(item)

            elif ret == offsets[3]: # New Comment
                content = Dialog().input(tr(30053), type=xbmcgui.INPUT_ALPHANUM)
                if content:
                    res = self.create_comment(content)

                    # Remove 'No Comments' item
                    if ccl.size() == 1 and ccl.getListItem(0).getLabel() == tr(30050):
                        ccl.reset()

                    item = self.create_list_item(res['id'], res['creator'], res['fullname'], content, 0, 0, 0, 0, res['profile_picture_url'], True)

                    ccl.addItem(item)
                    ccl.selectItem(ccl.size()-1)

            elif ret == offsets[4]: # Reply
                content = Dialog().input(tr(30054), type=xbmcgui.INPUT_ALPHANUM)
                if content:
                    res = self.create_comment(content, id)

                    # Insert new item by copying the list (no XMBC method to allow a fast insertion).
                    newItems = []
                    for i in range(selected_pos+1):
                        newItems.append(self.copy_list_item(ccl.getListItem(i)))
                    newItems.append(self.create_list_item(res['id'], res['creator'], res['fullname'], content, 0, 0, int(item.getProperty('indent'))+1, 0, res['profile_picture_url'], True))
                    for i in range(selected_pos+1, ccl.size()):
                        newItems.append(self.copy_list_item(ccl.getListItem(i)))

                    ccl.reset()
                    ccl.addItems(newItems)
                    ccl.selectItem(selected_pos+1)

            elif ret == offsets[5]: # Edit
                id = item.getProperty('id');
                content = item.getProperty('content')
                content = Dialog().input(tr(30045), type=xbmcgui.INPUT_ALPHANUM, defaultt=content)
                if content:
                    self.edit_comment(self.video_id, id, parent_id, creator, fullname, content)
                    item.setProperty('content', content)
                    self.refresh_label(item)

            elif ret == offsets[6]: # Remove 
                indentRemoved = item.getProperty('indent')

                self.remove_comment(self.video_id, id, parent_id, creator, fullname)

                ccl.removeItem(selected_pos)

                while True:
                    if selected_pos == ccl.size():
                        break
                    indent = ccl.getListItem(selected_pos).getProperty('indent')
                    if indent <= indentRemoved:
                        break
                    ccl.removeItem(selected_pos)

                if selected_pos > 0:
                    ccl.selectItem(selected_pos-1)

                if ccl.size() == 0:
                    ccl.addItem(ListItem(label=tr(30050)))

            elif ret == offsets[7]: # Refresh
                self.refresh()
        else:
            WindowXMLDialog.onAction(self, action)

        # If an action changes the selected item position refresh the label
        ccl = self.get_comment_control_list()
        if self.last_selected_position != ccl.getSelectedPosition():
            if self.last_selected_position >= 0 and self.last_selected_position < ccl.size():
                oldItem = ccl.getListItem(self.last_selected_position)
                if oldItem:
                    self.refresh_label(oldItem, False)
            newItem = ccl.getSelectedItem()
            if newItem:
                self.refresh_label(newItem, True)
            self.last_selected_position = ccl.getSelectedPosition()


    def fetch_comment_list(self):
        return bitchute_access.get_comments(self.video_id)

    def refresh(self):
        self.last_selected_position = -1
        progressDialog = xbmcgui.DialogProgress()
        progressDialog.create(tr(30048), tr(30049))

        try:
            ccl = self.get_comment_control_list()

            comments = self.fetch_comment_list()

            if len(comments):
                ccl.reset()

                # Items are returned newest to oldest which implies that child comments are always before their parents.
                # Iterate from oldest to newest comments building up a pre-order traversal ordering of the comment tree. Order
                # the tree roots by decreasing score (upvote_count-downvote_count).
                sort_indices = []
                i = 0
                while i < len(comments):
                    comment = comments[i]
                    comment_id = comment.id
                    if comment.parent_id:
                        for j in range(len(sort_indices)): # search for the parent in the sorted index list
                            sorted_item = comments[sort_indices[j][0]]
                            indent = sort_indices[j][1]
                            if sorted_item.id == comment.parent_id: # found the parent
                                # Insert at the end of the subtree of the parent. Use the indentation to figure
                                # out where the end is.
                                while j+1 < len(sort_indices):
                                    if sort_indices[j+1][1] > indent: # Item with index j+1 is in the child subtree
                                        j = j+1
                                    else: # Item with index j+1 is not in the child subtree. Break and insert before this item.
                                        break
                                sort_indices.insert(j+1, (i, indent+1, 0))
                                break
                    else:
                        upvotes = comment.upvote_count
                        downvotes = comment.downvote_count
                        score = upvotes-downvotes

                        j = 0
                        insert_index = len(sort_indices)
                        while j < len(sort_indices):
                            if sort_indices[j][1] == 0 and score > sort_indices[j][2]:
                                insert_index = j
                                break
                            j = j+1

                        sort_indices.insert(insert_index, (i, 0, score))

                    i = i + 1

                for (index,indent,score) in sort_indices:
                    comment = comments[index]
                    comment_id = comment.id
                    creator = comment.creator
                    fullname = comment.fullname
                    content = comment.content
                    upvote_count = comment.upvote_count
                    downvote_count = comment.downvote_count
                    profile_picture_url = comment.profile_picture_url
                    user_vote = comment.user_vote
                    created_by_current_user = comment.created_by_current_user

                    ccl.addItem(self.create_list_item(comment_id, creator, fullname, content, upvote_count, downvote_count, indent, user_vote, profile_picture_url, created_by_current_user))
                    if self.selected_comment_id and comment_id == self.selected_comment_id:
                        self.last_selected_position = ccl.size() - 1

                ccl.selectItem(self.last_selected_position)
            else:
                if ccl.size() == 0:
                    li = ListItem(label=tr(30050)) # No Comments
                    li.setProperty('indent', "0")
                    ccl.addItem(li)
        except Exception as e:
            progressDialog.update(100)
            progressDialog.close()
            raise e

        progressDialog.update(100)
        progressDialog.close()

    def get_comment_control_list(self) -> xbmcgui.ControlList:
        return typing.cast(xbmcgui.ControlList, self.getControl(1))

    def create_list_item(self, comment_id, creator, fullname, content, upvote_count, downvote_count, indent, user_vote, profile_picture_url, is_user):
        max_indent = 4
        li = ListItem(label=self.create_label(fullname, upvote_count, downvote_count, content, user_vote, False, is_user))
        li.setArt({'thumb': profile_picture_url})
        li.setProperty('id', comment_id)
        li.setProperty('creator', creator)
        li.setProperty('fullname', fullname)
        li.setProperty('upvote_count', str(upvote_count))
        li.setProperty('downvote_count', str(downvote_count))
        li.setProperty('content', content)
        li.setProperty('indent', str(indent if indent <= max_indent else max_indent))
        li.setProperty('user_vote', str(user_vote))
        li.setProperty('profile_picture_url', profile_picture_url)
        li.setProperty('is_user', str(1 if is_user else 0))
        return li

    def copy_list_item(self, li):
        li_copy = ListItem(label=li.getLabel())
        li_copy.setArt({'thumb': li.getArt('thumb')})
        li_copy.setProperty('id', li.getProperty('id'))
        li_copy.setProperty('creator', li.getProperty('creator'))
        li_copy.setProperty('fullname', li.getProperty('fullname'))
        li_copy.setProperty('upvote_count', li.getProperty('upvote_count'))
        li_copy.setProperty('downvote_count', li.getProperty('downvote_count'))
        li_copy.setProperty('content', li.getProperty('content'))
        li_copy.setProperty('indent', li.getProperty('indent'))
        li_copy.setProperty('user_vote', li.getProperty('user_vote'))
        li_copy.setProperty('profile_picture_url', li.getProperty('profile_picture_url'))
        li_copy.setProperty('is_user', li.getProperty('is_user'))
        return li_copy

    def refresh_label(self, li, selected=True):
        li.getProperty('id');
        fullname = li.getProperty('fullname')
        upvote_count = int(li.getProperty('upvote_count'))
        downvote_count = int(li.getProperty('downvote_count'))
        content = li.getProperty('content')
        indent = int(li.getProperty('indent'))
        user_vote = int(li.getProperty('user_vote'))
        profile_picture_url = li.getProperty('profile_picture_url')
        is_user = int(li.getProperty('is_user')) == 1
        li.setLabel(self.create_label(fullname, upvote_count, downvote_count, content, user_vote, selected, is_user))

    def create_label(self, fullname, upvote_count, downvote_count, content, user_vote, selected, is_user):
        if is_user:
            color = 'red' if selected else 'green'
            fullname = '[COLOR ' + color + ']' + fullname + '[/COLOR]'

        if user_vote == 1:
            upvote_count = '[COLOR green]' + str(upvote_count) + '[/COLOR]'
            downvote_count = str(downvote_count)
        elif user_vote == -1:
            upvote_count = str(upvote_count)
            downvote_count = '[COLOR green]' + str(downvote_count) + '[/COLOR]'
        else:
            upvote_count = str(upvote_count)
            downvote_count = str(downvote_count)

        lilabel = fullname
        lilabel += ' [COLOR orange]' + upvote_count + '/' + downvote_count + '[/COLOR]'
        lilabel += ' [COLOR white]' + content + '[/COLOR]'
        return lilabel

    def create_comment(self, content, parent_id=None):
        progressDialog = xbmcgui.DialogProgress()
        progressDialog.create(tr(30051), tr(30052))
        try:
            res = bitchute_access.create_comment(self.video_id, content, parent_id)
        except Exception as e:
            progressDialog.close()
            raise e
        progressDialog.close()
        return res

    def edit_comment(self, *args):
        bitchute_access.edit_comment(*args)

    def remove_comment(self, *args):
        bitchute_access.remove_comment(*args)

    def like(self, id, parent_id, creator, fullname):
        bitchute_access.vote_comment(self.video_id, id, parent_id, creator, fullname, 'like')

    def dislike(self, id, parent_id, creator, fullname):
        bitchute_access.vote_comment(self.video_id, id, parent_id, creator, fullname, 'dislike')

    def neutral(self, id, parent_id, creator, fullname):
        bitchute_access.vote_comment(self.video_id, id, parent_id, creator, fullname, '')

class CommentWindow:
    def __init__(self, video_id, selected_comment_id=''):
        file = 'addon-comments.xml' if addon.getSettingBool('display_comment_avatars') else 'addon-comments-noavatar.xml'
        window = CommentWindowXML(file, addon.getAddonInfo('path'), 'Default', video_id=video_id, selected_comment_id=selected_comment_id)
        window.doModal();
        del window

