"""Learning Module for ISL Practice"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Sign, SignLearningProgress
from datetime import datetime

learning_bp = Blueprint('learning', __name__, url_prefix='/api/learning')

@learning_bp.route('/signs', methods=['GET'])
@jwt_required()
def get_signs_for_learning():
    user_id = get_jwt_identity()
    category = request.args.get('category')
    difficulty = request.args.get('difficulty', 'Easy')
    
    query = Sign.query.filter_by(difficulty_level=difficulty)
    if category:
        query = query.filter_by(category=category)
    
    signs = query.all()
    return jsonify({'signs': [s.to_dict() for s in signs]}), 200

@learning_bp.route('/progress/<sign_id>', methods=['POST', 'PUT'])
@jwt_required(optional=True)
def update_learning_progress(sign_id):
    try:
        user_id = get_jwt_identity()
        if not user_id:
            user = User.query.first()
            user_id = user.id if user else 'anonymous'
        data = request.get_json() or {}
        
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
            accuracy = (progress.times_detected_correctly / progress.times_practiced) * 100
            progress.accuracy = round(accuracy, 1)
        
        progress.last_practiced = datetime.utcnow()
        
        if data.get('mastered') or progress.times_detected_correctly >= 1 or progress.accuracy >= 70.0:
            progress.mastered = True
        
        db.session.commit()
        
        return jsonify({
            'message': 'Practice progress recorded',
            'progress': progress.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error updating learning progress: {e}")
        return jsonify({'error': str(e)}), 500

@learning_bp.route('/progress', methods=['GET'])
@learning_bp.route('/summary', methods=['GET'])
@jwt_required(optional=True)
def get_learning_progress():
    try:
        user_id = get_jwt_identity()
        if not user_id:
            user = User.query.first()
            user_id = user.id if user else None

        limit = request.args.get('limit', 100, type=int)
        
        progress = SignLearningProgress.query.filter_by(user_id=user_id).order_by(
            SignLearningProgress.last_practiced.desc()
        ).limit(limit).all() if user_id else []
        
        total_signs_practiced = SignLearningProgress.query.filter(
            SignLearningProgress.user_id == user_id,
            SignLearningProgress.times_practiced > 0
        ).count() if user_id else 0
        
        mastered_signs = SignLearningProgress.query.filter(
            SignLearningProgress.user_id == user_id,
            SignLearningProgress.mastered == True
        ).count() if user_id else 0
        
        total_sessions = db.session.query(
            db.func.sum(SignLearningProgress.times_practiced)
        ).filter(SignLearningProgress.user_id == user_id).scalar() or 0 if user_id else 0
        
        avg_acc = db.session.query(
            db.func.avg(SignLearningProgress.accuracy)
        ).filter(SignLearningProgress.user_id == user_id).scalar() or 0.0 if user_id else 0.0
        
        stats_payload = {
            'total_signs_practiced': total_signs_practiced,
            'practiced_signs': total_signs_practiced,
            'total_mastered': mastered_signs,
            'mastered_signs': mastered_signs,
            'total_practiced': total_signs_practiced,
            'total_practice_sessions': total_sessions,
            'average_accuracy': round(float(avg_acc), 1)
        }
        
        return jsonify({
            **stats_payload,
            'progress': [p.to_dict() for p in progress],
            'stats': stats_payload,
            'summary': stats_payload
        }), 200
    except Exception as e:
        print(f"Error fetching progress: {e}")
        return jsonify({'error': str(e)}), 500

@learning_bp.route('/categories', methods=['GET'])
def get_categories():
    signs = Sign.query.all()
    categories = list(set(s.category for s in signs if s.category))
    return jsonify({'categories': categories}), 200
