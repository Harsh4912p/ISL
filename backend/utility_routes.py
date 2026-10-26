from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, SignLearningProgress, VideoSession, Sign, User
from dataset_loader import DatasetLoader
from datetime import datetime

utils_bp = Blueprint('utils', __name__, url_prefix='/api/utils')
dataset_loader = DatasetLoader()

@utils_bp.route('/dataset/load', methods=['POST'])
def load_dataset():
    try:
        count, message = dataset_loader.insert_signs_into_db()
        return jsonify({
            'message': message,
            'signs_loaded': count
        }), 200
    except Exception as e:
        return jsonify({'error': f'Failed to load dataset: {str(e)}'}), 500

@utils_bp.route('/dataset/stats', methods=['GET'])
def get_dataset_stats():
    try:
        stats = dataset_loader.get_dataset_statistics()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'error': f'Failed to fetch stats: {str(e)}'}), 500

@utils_bp.route('/learning-progress', methods=['GET'])
@jwt_required(optional=True)
def get_learning_progress():
    try:
        user_id = get_jwt_identity()
        if not user_id:
            user = User.query.first()
            user_id = user.id if user else None

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        if not user_id:
            return jsonify({'progress': [], 'total': 0, 'pages': 1, 'current_page': 1}), 200

        paginated_progress = SignLearningProgress.query.filter_by(
            user_id=user_id
        ).order_by(
            SignLearningProgress.accuracy.desc()
        ).paginate(page=page, per_page=per_page)

        return jsonify({
            'progress': [p.to_dict() for p in paginated_progress.items],
            'total': paginated_progress.total,
            'pages': paginated_progress.pages,
            'current_page': page
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to fetch progress: {str(e)}'}), 500

@utils_bp.route('/learning-progress/summary', methods=['GET'])
@jwt_required(optional=True)
def get_progress_summary():
    try:
        user_id = get_jwt_identity()
        if not user_id:
            user = User.query.first()
            user_id = user.id if user else None

        if not user_id:
            empty_summary = {
                'total_signs_practiced': 0,
                'practiced_signs': 0,
                'total_mastered': 0,
                'mastered_signs': 0,
                'total_practiced': 0,
                'total_practice_sessions': 0,
                'average_accuracy': 0.0
            }
            return jsonify({**empty_summary, 'summary': empty_summary, 'stats': empty_summary, 'recent': []}), 200

        # Count of distinct signs practiced
        total_signs_practiced = SignLearningProgress.query.filter(
            SignLearningProgress.user_id == user_id,
            SignLearningProgress.times_practiced > 0
        ).count()

        # Count of distinct signs mastered
        total_mastered = SignLearningProgress.query.filter(
            SignLearningProgress.user_id == user_id,
            SignLearningProgress.mastered == True
        ).count()

        total_sessions = db.session.query(
            db.func.sum(SignLearningProgress.times_practiced)
        ).filter(SignLearningProgress.user_id == user_id).scalar() or 0

        avg_accuracy = db.session.query(
            db.func.avg(SignLearningProgress.accuracy)
        ).filter(SignLearningProgress.user_id == user_id).scalar() or 0.0

        recent_progress = SignLearningProgress.query.filter_by(
            user_id=user_id
        ).order_by(
            SignLearningProgress.last_practiced.desc()
        ).limit(10).all()

        summary_data = {
            'total_signs_practiced': total_signs_practiced,
            'practiced_signs': total_signs_practiced,
            'total_mastered': total_mastered,
            'mastered_signs': total_mastered,
            'total_practiced': total_signs_practiced,
            'total_practice_sessions': total_sessions,
            'average_accuracy': round(float(avg_accuracy), 1)
        }

        return jsonify({
            **summary_data,
            'summary': summary_data,
            'stats': summary_data,
            'recent': [p.to_dict() for p in recent_progress]
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to fetch summary: {str(e)}'}), 500

@utils_bp.route('/learning-progress/<sign_id>', methods=['POST', 'PUT'])
@jwt_required(optional=True)
def update_learning_progress(sign_id):
    try:
        user_id = get_jwt_identity()
        if not user_id:
            user = User.query.first()
            user_id = user.id if user else 'anonymous'
        data = request.get_json() or {}

        sign = Sign.query.get(sign_id)
        if not sign:
            return jsonify({'error': 'Sign not found'}), 404

        progress = SignLearningProgress.query.filter_by(
            user_id=user_id,
            sign_id=sign_id
        ).first()

        if not progress:
            progress = SignLearningProgress(
                user_id=user_id,
                sign_id=sign_id,
                times_practiced=0,
                times_detected_correctly=0,
                accuracy=0.0,
                mastered=False
            )
            db.session.add(progress)

        if progress.times_practiced is None:
            progress.times_practiced = 0
        if progress.times_detected_correctly is None:
            progress.times_detected_correctly = 0

        times_inc = data.get('times_practiced', 1)
        progress.times_practiced += times_inc

        if data.get('correct') or data.get('times_detected_correctly'):
            correct_inc = data.get('times_detected_correctly', 1)
            progress.times_detected_correctly += correct_inc

        if progress.times_practiced > 0:
            progress.accuracy = round(
                (progress.times_detected_correctly / progress.times_practiced) * 100, 1
            )

        if data.get('mastered') or progress.times_detected_correctly >= 1 or progress.accuracy >= 70.0:
            progress.mastered = True

        progress.last_practiced = datetime.utcnow()

        db.session.commit()

        return jsonify({
            'message': 'Learning progress updated',
            'progress': progress.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update progress: {str(e)}'}), 500

@utils_bp.route('/video-sessions', methods=['POST'])
@jwt_required()
def create_video_session():
    try:
        user_id = get_jwt_identity()
        data = request.get_json() or {}

        session = VideoSession(
            user_id=user_id,
            session_type=data.get('session_type', 'live'),
            status='active'
        )

        db.session.add(session)
        db.session.commit()

        return jsonify({
            'message': 'Video session created',
            'session': session.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create session: {str(e)}'}), 500

@utils_bp.route('/video-sessions/<session_id>', methods=['PUT'])
@jwt_required()
def end_video_session(session_id):
    try:
        user_id = get_jwt_identity()

        session = VideoSession.query.filter_by(
            id=session_id,
            user_id=user_id
        ).first()

        if not session:
            return jsonify({'error': 'Session not found'}), 404

        data = request.get_json() or {}

        session.ended_at = datetime.utcnow()
        session.status = data.get('status', 'completed')

        if session.started_at and session.ended_at:
            duration = (session.ended_at - session.started_at).total_seconds()
            session.duration = int(duration)

        db.session.commit()

        return jsonify({
            'message': 'Video session ended',
            'session': session.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to end session: {str(e)}'}), 500

@utils_bp.route('/video-sessions', methods=['GET'])
@jwt_required()
def get_video_sessions():
    try:
        user_id = get_jwt_identity()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        paginated_sessions = VideoSession.query.filter_by(
            user_id=user_id
        ).order_by(VideoSession.started_at.desc()).paginate(page=page, per_page=per_page)

        return jsonify({
            'sessions': [s.to_dict() for s in paginated_sessions.items],
            'total': paginated_sessions.total,
            'pages': paginated_sessions.pages,
            'current_page': page
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to fetch sessions: {str(e)}'}), 500

@utils_bp.route('/categories', methods=['GET'])
def get_categories():
    try:
        categories = db.session.query(Sign.category).distinct().all()
        return jsonify({
            'categories': [str(cat[0]) for cat in categories if cat[0] is not None]
        }), 200
    except Exception as e:
        return jsonify({'error': f'Failed to fetch categories: {str(e)}'}), 500

@utils_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    }), 200
