"""
FiftyOne dataset permission related unit tests.

| Copyright 2017-2024, Voxel51, Inc.
| `voxel51.com <https://voxel51.com/>`_
|
"""

import unittest
from unittest import mock

import bson

import fiftyone as fo
from fiftyone.api import errors as api_errors
import fiftyone.core.dataset as fod
import fiftyone.core.runs as focr

from fiftyone.internal import context_vars, dataset_permissions
from fiftyone.internal.dataset_permissions import DatasetPermission


class DatasetPermissionTests(unittest.TestCase):
    def _assert_funcs_readonly(self, mutators, data_obj):
        for mutator, num_req_args in mutators:
            func = getattr(data_obj, mutator)
            req_args = [unittest.mock.Mock() for _ in range(num_req_args)]
            self.assertRaises(
                dataset_permissions.DatasetPermissionException, func, *req_args
            )

    def _assert_class_funcs_readonly(self, mutators, base_class, data_obj):
        for mutator, num_req_args in mutators:
            func = getattr(base_class, mutator)
            req_args = [unittest.mock.Mock() for _ in range(num_req_args)]
            self.assertRaises(
                dataset_permissions.DatasetPermissionException,
                func,
                data_obj,
                *req_args
            )

    def _assert_setters_readonly(self, setters, data_obj):
        for setter in setters:
            self.assertRaises(
                dataset_permissions.DatasetPermissionException,
                setattr,
                data_obj,
                setter,
                unittest.mock.Mock(),
            )

    def test_dataset_edit_permissions(self):
        fo.delete_non_persistent_datasets()
        dataset_name = self.test_dataset_edit_permissions.__name__
        dataset = fo.Dataset(dataset_name)

        sample = fo.Sample("/blah.mp4", foo="bar")
        sample["detections"] = fo.Detections(
            detections=[fo.Detection(label="blah")]
        )
        frame = fo.Frame(
            quality=97.12,
            weather=fo.Classification(label="sunny"),
            objects=fo.Detections(
                detections=[
                    fo.Detection(
                        label="cat", bounding_box=[0.1, 0.1, 0.2, 0.2]
                    ),
                    fo.Detection(
                        label="dog", bounding_box=[0.7, 0.7, 0.2, 0.2]
                    ),
                ]
            ),
        )
        sample.frames[1] = frame

        dataset.add_sample(sample)

        for the_perm in (
            DatasetPermission.NO_ACCESS,
            DatasetPermission.VIEW,
            DatasetPermission.TAG,
        ):
            dataset._Dataset__permission = the_perm
            view = dataset.limit(10)

            # Collection
            collection_mutators = [
                ("split_labels", 2),
                ("merge_labels", 2),
                ("set_values", 2),
                ("set_label_values", 2),
                ("compute_metadata", 0),
                ("apply_model", 1),
                ("evaluate_regressions", 1),
                ("evaluate_classifications", 1),
                ("evaluate_detections", 1),
                ("evaluate_segmentations", 1),
                ("rename_evaluation", 2),
                ("create_index", 1),
                ("drop_index", 1),
                ("delete_evaluation", 1),
                ("delete_evaluations", 0),
                ("rename_brain_run", 2),
                ("delete_brain_run", 1),
                ("delete_brain_runs", 0),
                ("register_run", 2),
                ("rename_run", 2),
                ("update_run_config", 2),
                ("save_run_results", 2),
                ("delete_run", 1),
                ("delete_runs", 0),
                ("annotate", 1),
                ("load_annotations", 1),
                ("rename_annotation_run", 2),
                ("delete_annotation_run", 1),
                ("delete_annotation_runs", 0),
                ("save_context", 0),
            ]
            for the_collection in (dataset, view):
                self._assert_funcs_readonly(
                    collection_mutators, the_collection
                )

            self.assertRaises(
                dataset_permissions.DatasetPermissionException,
                fo.core.collections.SaveContext,
                dataset,
            )

            self.assertRaises(
                dataset_permissions.DatasetPermissionException,
                dataset.compute_embeddings,
                unittest.mock.Mock(),
                embeddings_field="field",
            )
            self.assertRaises(
                dataset_permissions.DatasetPermissionException,
                dataset.compute_patch_embeddings,
                unittest.mock.Mock(),
                unittest.mock.Mock(),
                embeddings_field="field",
            )
            self.assertRaises(
                dataset_permissions.DatasetPermissionException,
                dataset.to_frames,
                sample_frames=True,
            )
            sort_similarity_stage = fo.core.stages.SortBySimilarity(
                [bson.ObjectId()], dist_field="something"
            )
            self.assertRaises(
                dataset_permissions.DatasetPermissionException,
                sort_similarity_stage.validate,
                dataset,
            )
            to_frames_stage = fo.core.stages.ToFrames(
                config={"sample_frames": True}
            )
            self.assertRaises(
                dataset_permissions.DatasetPermissionException,
                to_frames_stage.load_view,
                dataset,
            )

            # Allowed on collections
            dataset.take(5).values("filepath")
            dataset.shuffle().values("filepath")
            dataset.sort_by("filepath").values("filepath")

            # Dataset
            dataset_setters = [
                "media_type",
                "persistent",
                "info",
                "app_config",
                "classes",
                "default_classes",
                "mask_targets",
                "default_mask_targets",
                "skeletons",
                "default_skeleton",
                "default_group_slice",
            ]
            self._assert_setters_readonly(dataset_setters, dataset)

            dataset_mutators = [
                ("add_sample_field", 2),
                ("add_dynamic_sample_fields", 0),
                ("add_frame_field", 2),
                ("add_dynamic_frame_fields", 0),
                ("add_group_field", 1),
                ("rename_sample_field", 2),
                ("rename_sample_fields", 1),
                ("rename_frame_field", 2),
                ("rename_frame_fields", 1),
                ("clone_sample_field", 2),
                ("clone_sample_fields", 1),
                ("clone_frame_field", 2),
                ("clone_frame_fields", 1),
                ("clear_sample_field", 1),
                ("clear_sample_fields", 1),
                ("clear_frame_field", 1),
                ("clear_frame_fields", 1),
                ("delete_sample_field", 1),
                ("delete_sample_fields", 1),
                ("remove_dynamic_sample_field", 1),
                ("remove_dynamic_sample_fields", 1),
                ("delete_frame_field", 1),
                ("delete_frame_fields", 1),
                ("remove_dynamic_frame_field", 1),
                ("remove_dynamic_frame_fields", 1),
                ("add_group_slice", 2),
                ("rename_group_slice", 2),
                ("delete_group_slice", 1),
                ("add_sample", 1),
                ("add_samples", 1),
                ("add_collection", 1),
                ("merge_sample", 1),
                ("merge_samples", 1),
                ("delete_samples", 1),
                ("delete_frames", 1),
                ("delete_groups", 1),
                ("delete_labels", 0),
                ("remove_sample", 1),
                ("remove_samples", 1),
                ("save", 0),
                ("save_view", 2),
                ("update_saved_view_info", 2),
                ("delete_saved_view", 1),
                ("delete_saved_views", 0),
                ("clear", 0),
                ("clear_frames", 0),
                ("ensure_frames", 0),
                ("delete", 0),
                ("add_dir", 0),
                ("merge_dir", 0),
                ("add_archive", 1),
                ("merge_archive", 1),
                ("add_importer", 1),
                ("merge_importer", 1),
                ("add_images", 1),
                ("add_labeled_images", 2),
                ("add_images_dir", 1),
                ("add_images_patt", 1),
                ("ingest_images", 1),
                ("ingest_labeled_images", 2),
                ("add_videos", 1),
                ("add_labeled_videos", 2),
                ("add_videos_dir", 1),
                ("add_videos_patt", 1),
                ("ingest_videos", 1),
                ("ingest_labeled_videos", 2),
            ]
            self._assert_funcs_readonly(dataset_mutators, dataset)

            # Dataset Iter samples and groups
            dataset.iter_samples()
            self.assertRaises(
                dataset_permissions.DatasetPermissionException,
                dataset.iter_samples,
                autosave=True,
            )
            dataset.iter_groups()
            self.assertRaises(
                dataset_permissions.DatasetPermissionException,
                dataset.iter_groups,
                autosave=True,
            )

            # View
            self.assertEqual(view._permission, the_perm)

            view_setters = [
                "tags",
                "description",
                "info",
                "app_config",
                "classes",
                "default_classes",
                "mask_targets",
                "default_mask_targets",
                "skeletons",
                "default_skeleton",
            ]
            self._assert_setters_readonly(view_setters, view)

            view_mutators = [
                ("clone_sample_field", 2),
                ("clone_sample_fields", 1),
                ("clone_frame_field", 2),
                ("clone_frame_fields", 1),
                ("clear_sample_field", 1),
                ("clear_sample_fields", 1),
                ("clear_frame_field", 1),
                ("clear_frame_fields", 1),
                ("clear", 0),
                ("clear_frames", 0),
                ("keep", 0),
                ("keep_fields", 0),
                ("keep_frames", 0),
                ("ensure_frames", 0),
                ("save", 0),
            ]
            self._assert_funcs_readonly(view_mutators, view)

            # View Iter samples and groups
            view.iter_samples()
            self.assertRaises(
                dataset_permissions.DatasetPermissionException,
                view.iter_samples,
                autosave=True,
            )
            view.iter_groups()
            self.assertRaises(
                dataset_permissions.DatasetPermissionException,
                view.iter_groups,
                autosave=True,
            )

            # Sample
            sample = dataset.first()
            self.assertEqual(sample._permission, the_perm)
            self.assertRaises(
                dataset_permissions.DatasetPermissionException,
                sample.__setattr__,
                "foo",
                unittest.mock.Mock(),
            )
            self.assertRaises(
                dataset_permissions.DatasetPermissionException,
                sample.__setitem__,
                "foo2",
                unittest.mock.Mock(),
            )

            # SampleView
            sample_view = view.first()
            self.assertEqual(sample_view._permission, the_perm)

            sample_mixin_mutators = [
                ("set_field", 2),
                ("clear_field", 1),
                ("add_labels", 1),
                ("merge", 1),
                ("save", 0),
            ]
            for mixin_sample in (sample, sample_view):
                self._assert_funcs_readonly(
                    sample_mixin_mutators, mixin_sample
                )

            # Runs
            runs_mutators = [
                ("update_run_key", 2),
                ("save_run_info", 1),
                ("update_run_config", 2),
                ("save_run_results", 2),
                ("delete_run", 1),
                ("delete_runs", 0),
            ]
            for sample_collection in (dataset, view):
                self._assert_class_funcs_readonly(
                    runs_mutators, focr.Run, sample_collection
                )

            run_config = fo.core.runs.RunConfig()
            run = fo.core.runs.Run(run_config)
            self.assertRaises(
                dataset_permissions.DatasetPermissionException,
                run.register_run,
                dataset,
                "blah",
            )
            run_results = fo.core.runs.RunResults(
                dataset, {}, "blah", backend="blah"
            )
            self.assertRaises(
                dataset_permissions.DatasetPermissionException,
                run_results.save,
            )
            self.assertRaises(
                dataset_permissions.DatasetPermissionException,
                run_results.save_config,
            )

            # Frames
            frames = sample.frames
            self.assertEqual(frames._permission, the_perm)

            frames_mutators = [
                ("add_frame", 2),
                ("delete_frame", 1),
                ("update", 1),
                ("merge", 1),
                ("clear", 0),
                ("save", 0),
                ("__delitem__", 1),
                ("__setitem__", 2),
            ]

            # FramesView
            frames_view = view.first().frames
            self.assertEqual(frames_view._permission, the_perm)
            self.assertRaises(
                dataset_permissions.DatasetPermissionException,
                frames_view.save,
            )
            self.assertRaises(
                dataset_permissions.DatasetPermissionException,
                frames_view.add_frame,
                2,
                frame,
            )

            for frames_obj in (frames, frames_view):
                self._assert_funcs_readonly(frames_mutators, frames_obj)

            # Frame
            frame = frames[1]
            self.assertEqual(frame._permission, the_perm)

            # FrameView
            frame_view = frames_view[1]
            self.assertEqual(frame_view._permission, the_perm)

            # DocumentView
            document_mutators = [
                ("set_field", 2),
                ("update_fields", 1),
                ("clear_field", 1),
                ("save", 0),
                ("merge", 1),
            ]
            for document_obj in (sample_view, frame_view, frame, frame_view):
                self._assert_funcs_readonly(document_mutators, document_obj)

            # Clips
            clips = dataset.to_clips("frames.objects")
            clips_mutators = [
                ("set_values", 1),
                ("set_label_values", 1),
                ("save", 0),
                ("keep", 0),
                ("keep_fields", 0),
            ]
            self._assert_funcs_readonly(clips_mutators, clips)

            # Trajectories
            trajs = dataset.to_trajectories("frames.objects")
            self.assertEqual(trajs._permission, the_perm)
            trajs_mutators = [
                ("set_values", 1),
                ("set_label_values", 1),
                ("save", 0),
                ("keep", 0),
                ("keep_fields", 0),
            ]
            self._assert_funcs_readonly(trajs_mutators, trajs)

            # To Frames
            to_frames = dataset.to_frames()
            self.assertEqual(to_frames._permission, the_perm)
            to_frames_mutators = [
                ("set_values", 1),
                ("set_label_values", 1),
                ("save", 0),
                ("keep", 0),
                ("keep_fields", 0),
            ]
            self._assert_funcs_readonly(to_frames_mutators, to_frames)

            # Crazy view
            crazy_patches = (
                dataset.limit(51)
                .to_clips("frames.objects")
                .limit(51)
                .to_frames()
                .limit(10)
                .to_patches("objects")
            )
            self.assertEqual(crazy_patches._permission, the_perm)
            patches_mutators = [
                ("set_values", 1),
                ("set_label_values", 1),
                ("save", 0),
                ("keep", 0),
                ("keep_fields", 0),
            ]
            self._assert_funcs_readonly(patches_mutators, crazy_patches)

        # We can now
        dataset._Dataset__permission = DatasetPermission.EDIT
        dataset.add_sample_field("test_edit_field", fo.StringField)
        sample.set_field("blah", "blor")

    def test_dataset_tag_permissions(self):
        fo.delete_non_persistent_datasets()
        dataset_name = self.test_dataset_tag_permissions.__name__
        dataset = fo.Dataset(dataset_name)
        dataset.add_sample(fo.Sample("/path/to/image.png"))

        for the_perm in (DatasetPermission.NO_ACCESS, DatasetPermission.VIEW):
            dataset._Dataset__permission = the_perm
            view = dataset.limit(1)

            self.assertEqual(view._permission, the_perm)

            tagging_mutators = [
                ("tag_samples", 1),
                ("untag_samples", 1),
                ("tag_labels", 1),
                ("untag_labels", 1),
            ]

            for the_collection in (dataset, view):
                self._assert_funcs_readonly(tagging_mutators, the_collection)

        # We can now
        dataset._Dataset__permission = DatasetPermission.TAG
        dataset.tag_samples("blah")
        dataset.untag_samples("blah")

    def test_dataset_manage_permissions(self):
        fo.delete_non_persistent_datasets()
        dataset_name = self.test_dataset_manage_permissions.__name__
        dataset = fo.Dataset(dataset_name)

        for the_perm in (
            DatasetPermission.NO_ACCESS,
            DatasetPermission.VIEW,
            DatasetPermission.TAG,
            DatasetPermission.EDIT,
        ):
            dataset._Dataset__permission = the_perm

            # Dataset
            manage_setters = [
                "name",
                "tags",
                "description",
            ]
            self._assert_setters_readonly(manage_setters, dataset)

        # Now we can
        dataset._Dataset__permission = DatasetPermission.MANAGE
        dataset.tags = ["test", "me"]

    def test_dataset_patches_permissions(self):
        fo.delete_non_persistent_datasets()
        dataset_name = self.test_dataset_patches_permissions.__name__
        dataset = fo.Dataset(dataset_name)

        sample = fo.Sample("/blah.jpg", foo="bar")
        sample["detections"] = fo.Detections(
            detections=[fo.Detection(label="blah")]
        )
        dataset.add_sample(sample)

        for the_perm in (
            DatasetPermission.NO_ACCESS,
            DatasetPermission.VIEW,
            DatasetPermission.TAG,
        ):
            dataset._Dataset__permission = the_perm
            # Patches
            patches = dataset.to_patches("detections")
            self.assertEqual(patches._permission, the_perm)
            patches_mutators = [
                ("set_values", 1),
                ("set_label_values", 1),
                ("save", 0),
                ("keep", 0),
                ("keep_fields", 0),
            ]
            self._assert_funcs_readonly(patches_mutators, patches)


class LoadDatasetPermissionsTests(unittest.TestCase):
    def test_dataset_no_singleton(self):
        fo.delete_non_persistent_datasets()
        dataset = self.test_dataset_no_singleton.__name__
        orig_dataset = fo.Dataset(dataset)
        self.assertIs(fo.Dataset._instances[dataset], orig_dataset)

        reset_token = context_vars.no_singleton_cache.set(True)
        try:
            ds = fo.load_dataset(dataset)
            self.assertIsNot(ds, orig_dataset)
        finally:
            context_vars.no_singleton_cache.reset(reset_token)

    def test_dataset_rename_non_singleton(self):
        fo.delete_non_persistent_datasets()
        dataset = self.test_dataset_no_singleton.__name__
        orig_dataset = fo.Dataset(dataset)

        reset_token = context_vars.no_singleton_cache.set(True)
        try:
            ds = fo.load_dataset(dataset)
            ds.name = "new name who dis"
            self.assertEqual(orig_dataset.name, ds.name)
            self.assertIs(fo.Dataset._instances[ds.name], orig_dataset)
            self.assertIsNot(ds, orig_dataset)
        finally:
            context_vars.no_singleton_cache.reset(reset_token)

    def test_load_dataset_with_no_permissions(self):
        fo.delete_non_persistent_datasets()
        dataset = self.test_load_dataset_with_no_permissions.__name__
        fo.Dataset(dataset)
        fo.Dataset._instances.clear()
        ds = fo.load_dataset(dataset)
        self.assertIsNone(ds._permission)

    @mock.patch.object(
        fo.core.dataset.dataset_permissions,
        "get_dataset_permissions_for_current_user",
    )
    def test_load_dataset_with_permissions(
        self, get_dataset_permissions_for_current_user_mock
    ):
        fo.delete_non_persistent_datasets()
        get_dataset_permissions_for_current_user_mock.return_value = (
            dataset_permissions.DatasetPermission.EDIT
        )
        dataset = self.test_load_dataset_with_permissions.__name__
        user_id = "test_user123"
        fo.Dataset(dataset)
        fo.Dataset._instances.clear()
        reset_token = context_vars.running_user_id.set(user_id)
        try:
            ds = fo.load_dataset(dataset)
            self.assertEqual(
                ds._permission, dataset_permissions.DatasetPermission.EDIT
            )
            get_dataset_permissions_for_current_user_mock.assert_called_with(
                dataset
            )
        finally:
            context_vars.running_user_id.reset(reset_token)

    @mock.patch.object(
        fo.core.dataset.dataset_permissions,
        "get_dataset_permissions_for_current_user",
    )
    def test_virtual_no_permissions(
        self, get_dataset_permissions_for_current_user_mock
    ):
        fo.delete_non_persistent_datasets()
        dataset = self.test_virtual_no_permissions.__name__

        fo.Dataset(dataset)
        fo.Dataset._instances.clear()

        ds = fo.Dataset(dataset, _create=False, _virtual=True)
        get_dataset_permissions_for_current_user_mock.assert_not_called()
        ds.delete()

    @mock.patch.object(
        fo.core.dataset.dataset_permissions.api_requests,
        "get_dataset_permissions_for_user",
    )
    def test_generated_virtual(self, get_dataset_permissions_for_user_mock):
        fo.delete_non_persistent_datasets()
        dataset = self.test_virtual_no_permissions.__name__
        get_dataset_permissions_for_user_mock.return_value = "NO_ACCESS"

        ds = fo.Dataset(dataset)
        sample = fo.Sample("/blah.jpg", foo="bar")
        sample["detections"] = fo.Detections(
            detections=[
                fo.Detection(label="blah", bounding_box=[0.1, 0.2, 0.3, 0.4])
            ]
        )
        sample["ground_truth"] = fo.Detections(
            detections=[
                fo.Detection(label="blah", bounding_box=[0.1, 0.2, 0.3, 0.4])
            ]
        )
        ds.add_sample(sample)
        ds.evaluate_detections("detections", eval_key="eval")

        patches = ds.to_patches("detections")
        eval_patches = ds.to_evaluation_patches("eval")
        ds.save_view("patches", patches)
        ds.save_view("eval_patches", eval_patches)
        fo.Dataset._instances.clear()

        loaded = ds.load_saved_view("patches")
        loaded = ds.load_saved_view("eval_patches")

        ds.delete()

    @mock.patch.object(
        fo.core.dataset.dataset_permissions.api_requests,
        "get_dataset_permissions_for_user",
    )
    def test_video_generated_virtual(
        self, get_dataset_permissions_for_user_mock
    ):
        fo.delete_non_persistent_datasets()
        dataset = self.test_virtual_no_permissions.__name__

        def _load_self_but_nothing_else(name, _):
            if name == dataset:
                return dataset_permissions.DatasetPermission.EDIT.name
            return dataset_permissions.DatasetPermission.NO_ACCESS.name

        get_dataset_permissions_for_user_mock.side_effect = (
            _load_self_but_nothing_else
        )

        ds = fo.Dataset(dataset)
        sample = fo.Sample("/blah.mp4", foo="bar")
        sample["detections"] = fo.Detections(
            detections=[fo.Detection(label="blah")]
        )
        frame = fo.Frame(
            quality=97.12,
            weather=fo.Classification(label="sunny"),
            objects=fo.Detections(
                detections=[
                    fo.Detection(
                        label="cat", bounding_box=[0.1, 0.1, 0.2, 0.2]
                    ),
                    fo.Detection(
                        label="dog", bounding_box=[0.7, 0.7, 0.2, 0.2]
                    ),
                ]
            ),
        )
        sample.frames[1] = frame

        ds.add_sample(sample)

        clips = ds.to_clips("frames.objects")
        frames = ds.to_frames()
        trajs = ds.to_trajectories("frames.objects")
        ds.save_view("clips", clips)
        ds.save_view("frames", frames)
        ds.save_view("trajs", trajs)

        fo.Dataset._instances.clear()

        loaded = ds.load_saved_view("clips")
        loaded = ds.load_saved_view("frames")
        loaded = ds.load_saved_view("trajs")

        ds.delete()

    @mock.patch.object(
        fo.core.dataset.dataset_permissions.api_requests,
        "get_dataset_permissions_for_user",
    )
    def test_load_non_persistent(self, get_dataset_permissions_for_user_mock):
        fo.delete_non_persistent_datasets()
        dataset = self.test_load_non_persistent.__name__

        get_dataset_permissions_for_user_mock.return_value = (
            dataset_permissions.DatasetPermission.NO_ACCESS.name
        )
        ds = fo.Dataset(dataset)

        fo.Dataset._instances.clear()

        ds2 = fo.load_dataset(dataset)
        self.assertEqual(ds2.name, dataset)

        ds.delete()


class CreateDatasetWithPermissionsTests(unittest.TestCase):
    def test_create_dataset_with_no_permissions(self):
        fo.delete_non_persistent_datasets()
        dataset = self.test_create_dataset_with_no_permissions.__name__

        # Create persistent dataset with no user_id should have no perms
        ds = fo.Dataset(dataset, persistent=False)
        self.assertIsNone(ds._permission)
        ds.delete()

        # Create nonpersistent dataset even with user_id set should have no perms
        user_id = "testuser1234"
        reset_token = context_vars.running_user_id.set(user_id)
        try:
            ds = fo.Dataset(dataset, persistent=False)
            self.assertIsNone(ds._permission)
            ds.delete()
        finally:
            context_vars.running_user_id.reset(reset_token)

    @mock.patch.object(
        dataset_permissions,
        "create_dataset_with_current_user_permissions",
    )
    def test_create_dataset_with_permissions(
        self, create_dataset_with_current_user_permissions_mock
    ):
        fo.delete_non_persistent_datasets()
        create_dataset_with_current_user_permissions_mock.return_value = True
        dataset = self.test_create_dataset_with_permissions.__name__

        # Passes permission error down
        create_dataset_with_current_user_permissions_mock.side_effect = (
            api_errors.FiftyOneTeamsAPIError
        )
        self.assertRaises(
            api_errors.FiftyOneTeamsAPIError,
            fo.Dataset,
            dataset,
            persistent=True,
        )
        create_dataset_with_current_user_permissions_mock.assert_called_with(
            dataset
        )

        create_dataset_with_current_user_permissions_mock.reset_mock()

        def _make_dataset_docs(dataset):
            fo.core.dataset._create_dataset(self, dataset, persistent=True)
            fo.Dataset._instances.clear()
            return True

        create_dataset_with_current_user_permissions_mock.side_effect = (
            _make_dataset_docs
        )

        ds = fo.Dataset(dataset, persistent=True)

        self.assertEqual(
            ds._permission, dataset_permissions.DatasetPermission.MANAGE
        )
        create_dataset_with_current_user_permissions_mock.assert_called_with(
            dataset
        )
        ds.delete()

    @mock.patch.object(
        dataset_permissions,
        "running_in_user_context",
    )
    def test_cant_upgrade_persistence(self, running_in_user_context_mock):
        fo.delete_non_persistent_datasets()
        running_in_user_context_mock.return_value = True
        dataset = self.test_cant_upgrade_persistence.__name__
        ds = fo.Dataset(dataset, persistent=False)
        self.assertRaises(NotImplementedError, setattr, ds, "persistent", True)
        ds.delete()


class ListDatasetsWithPermissionsTests(unittest.TestCase):
    @mock.patch.object(fo.core.dataset, "_list_datasets")
    @mock.patch.object(fo.core.dataset, "_list_datasets_info")
    @mock.patch.object(
        dataset_permissions,
        "list_datasets_for_current_user",
    )
    def test_list_with_no_permissions(
        self,
        list_datasets_for_current_user_mock,
        _list_datasets_info_mock,
        _list_datasets_mock,
    ):
        list_datasets_for_current_user_mock.return_value = None

        glob_patt, tags = mock.Mock(), mock.Mock()

        for info, list_mock, other_mock in [
            (False, _list_datasets_mock, _list_datasets_info_mock),
            (True, _list_datasets_info_mock, _list_datasets_mock),
        ]:
            list_datasets_for_current_user_mock.reset_mock()
            _list_datasets_mock.reset_mock()
            _list_datasets_info_mock.reset_mock()

            #####
            self.assertEqual(
                fo.core.dataset.list_datasets(
                    glob_patt=glob_patt, tags=tags, info=info
                ),
                list_mock.return_value,
            )
            #####

            list_datasets_for_current_user_mock.assert_called_once_with(
                glob_patt=glob_patt, tags=tags, info=info
            )
            list_mock.assert_called_with(glob_patt=glob_patt, tags=tags)
            other_mock.assert_not_called()

    @mock.patch.object(
        dataset_permissions,
        "list_datasets_for_current_user",
    )
    def test_list_with_permissions(
        self,
        list_datasets_for_current_user_mock,
    ):
        glob_patt, tags, info = mock.Mock(), mock.Mock(), mock.Mock()

        #####
        self.assertEqual(
            fo.core.dataset.list_datasets(
                glob_patt=glob_patt, tags=tags, info=info
            ),
            list_datasets_for_current_user_mock.return_value,
        )
        #####