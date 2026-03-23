CREATE TABLE IF NOT EXISTS tajwid_exam_results (
    id BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT(20) UNSIGNED NOT NULL,
    total_questions INT(11) NOT NULL,
    correct_answers INT(11) NOT NULL,
    pronunciation_avg_score DECIMAL(5,2) NULL,
    pronunciation_question_count INT(11) NULL,
    score INT(11) NULL,
    final_score DECIMAL(5,2) NULL,
    xp_earned INT(11) NULL,
    started_at DATETIME NULL,
    finished_at DATETIME NULL,
    created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_tajwid_exam_results_user_id (user_id)
);
