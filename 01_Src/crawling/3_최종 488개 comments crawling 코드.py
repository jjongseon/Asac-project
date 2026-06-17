import os
import re
import time
import requests
import pandas as pd

# 1. 칭호 세분화 파싱
def parse_badges_to_dict(badges_list):
    badge_data = {
        'is_pledge_master': False, 'is_backer': False, 
        'backer_number': None, 'is_prior_backer': False, 'is_pathfinder': False
    }
    if not badges_list: return badge_data
    for b in badges_list:
        b_type = b.get('badgeType')
        b_num = b.get('backerNumber')
        if b_type == 1: badge_data['is_pledge_master'] = True
        elif b_type == 3: badge_data['is_backer'] = True; badge_data['backer_number'] = b_num
        elif b_type == 4: badge_data['is_prior_backer'] = True
        elif b_type == 5: badge_data['is_pathfinder'] = True
    return badge_data

# 2. 확실한 project_url을 이용한 Thread ID 추출
def extract_thread_id_from_url(project_url, headers):
    target_url = project_url if str(project_url).endswith('/comments') else f"{project_url}/comments"
    try:
        res = requests.get(target_url, headers=headers, timeout=10)
        if res.status_code == 200:
            match = re.search(r'"commentThreadID":\s*(\d+)', res.text)
            if match: return int(match.group(1))
    except Exception: pass
    return None

# 3-1. API 조회를 위한 모든 작성자 ID 추출
def get_all_author_ids_recursive(items):
    author_ids = set()
    for item in items:
        if item.get('authorID') is not None: author_ids.add(item.get('authorID'))
        children = item.get('children')
        if children: author_ids.update(get_all_author_ids_recursive(children))
    return list(author_ids)

# 3-2. 계층 구조(부모-자식)를 유지하며 데이터 병합
def extract_comments_recursive(items, user_mapping, project_id, current_depth=0, fallback_parent_id=None):
    extracted_data = []
    for item in items:
        author_raw = item.get('authorID')
        author_id = str(author_raw) if author_raw is not None else None
        user_info = user_mapping.get(author_id, {}) if author_id else {}
        badges_dict = parse_badges_to_dict(user_info.get('badges', []))
        
        children_count = item.get('childrenTotalCount', 0)
        actual_parent_id = item.get('parentID') or fallback_parent_id
        current_comment_id = item.get('commentID')
        
        comment_dict = {
            'project_ID': project_id, 'comment_id': current_comment_id,
            'parent_id': actual_parent_id, 'depth_level': current_depth,
            'author_id': author_id, 'author_name': user_info.get('nickname', 'Unknown'),
            'creator_id': item.get('authorType', 0), 
            'is_pledge_master': badges_dict['is_pledge_master'], 'is_backer': badges_dict['is_backer'],
            'backer_number': badges_dict['backer_number'], 'is_prior_backer': badges_dict['is_prior_backer'],
            'is_pathfinder': badges_dict['is_pathfinder'], 'has_children': bool(children_count > 0),
            'children_count': children_count, 'text': item.get('text'),
            'created_at': item.get('createdAt'), 'likes': item.get('likesCount')
        }
        extracted_data.append(comment_dict)
        
        children_list = item.get('children')
        if children_list:
            extracted_data.extend(
                extract_comments_recursive(children_list, user_mapping, project_id, current_depth + 1, current_comment_id)
            )
    return extracted_data

# 4. 부모 댓글 내부에 숨겨진(Paginated) 대댓글 추가 수집
def fetch_missing_replies(thread_id, parent_id, start_last_id, start_last_score, headers):
    missing_replies = []
    current_last_id, current_last_score = start_last_id, start_last_score
    while True:
        payload = {
            "GetCommentsForCurrentUser": False, "commentID": None, "commentThreadID": thread_id, "freshCommentID": None,
            "getCommentsWithCreatorInput": False, "highlightedCommentID": None, "lastFetchedCommentID": current_last_id, 
            "lastPinnedAt": None, "lastScore": current_last_score, "parentID": parent_id, "selectedCommentFilter": None, "sortType": 0, "tag": None
        }
        try: res = requests.post("https://gamefound.com/api/comments/getComments", headers=headers, json=payload, timeout=10)
        except Exception: break
        if res.status_code != 200: break
        items = res.json().get('data', {}).get('pagedItems', [])
        if not items: break
        missing_replies.extend(items)
        last_item = items[-1]
        current_last_id, current_last_score = last_item.get("commentID"), last_item.get("score", last_item.get("likesCount", 0))
        time.sleep(0.5) 
    return missing_replies

# 5. 단일 프로젝트 리뷰 메인 루프
def fetch_single_project_comments(project_id, thread_id, headers):
    comment_api_url = "https://gamefound.com/api/comments/getComments"
    author_api_url = "https://gamefound.com/api/comments/getCommentsAuthors"
    comment_list = []
    last_fetched_id, last_pinned_at, last_score = None, None, None
    seen_comment_ids = set()
    
    while True:
        payload = {
            "GetCommentsForCurrentUser": False, "commentID": None, "commentThreadID": thread_id, "freshCommentID": None,
            "getCommentsWithCreatorInput": False, "highlightedCommentID": None, "lastFetchedCommentID": last_fetched_id, 
            "lastPinnedAt": last_pinned_at, "lastScore": last_score, "selectedCommentFilter": None, "sortType": 0, "tag": None
        }
        try: res_comments = requests.post(comment_api_url, headers=headers, json=payload, timeout=10)
        except Exception: break
        if res_comments.status_code != 200: break
            
        items = res_comments.json().get('data', {}).get('pagedItems', [])
        if not items: break
            
        new_items = []
        for item in items:
            cid = item.get('commentID')
            if cid not in seen_comment_ids:
                new_items.append(item)
                seen_comment_ids.add(cid)
                
        if not new_items: break
        
        for item in new_items:
            total_children = item.get('childrenTotalCount', 0)
            existing_children = item.get('children', [])
            if existing_children is None: 
                existing_children = []
                item['children'] = existing_children
                
            if total_children > len(existing_children):
                last_child = existing_children[-1] if existing_children else None
                start_id = last_child.get('commentID') if last_child else None
                start_score = last_child.get('score', last_child.get('likesCount', 0)) if last_child else None
                parent_id = item.get('commentID')
                
                extra_replies = fetch_missing_replies(thread_id, parent_id, start_id, start_score, headers)
                item['children'].extend(extra_replies)

        author_ids = get_all_author_ids_recursive(new_items)
        user_mapping = {}
        if author_ids:
            try:
                res_authors = requests.post(author_api_url, headers=headers, json={"authorIDs": author_ids, "commentThreadID": thread_id}, timeout=10)
                if res_authors.status_code == 200: user_mapping = res_authors.json().get('data', {})
            except Exception: pass

        parsed_comments = extract_comments_recursive(new_items, user_mapping, project_id, current_depth=0)
        comment_list.extend(parsed_comments)
        
        last_item = items[-1]
        last_fetched_id, last_pinned_at, last_score = last_item.get("commentID"), last_item.get("pinnedAt"), last_item.get("score", last_item.get("likesCount", 0))
        time.sleep(1.0) 
        
    return comment_list

# 6. 전체 실행 및 저장(이어하기) 컨트롤러
def run_mass_crawler(project_csv_path, save_dir):
    if not os.path.exists(project_csv_path): 
        print(f"❌ 원본 파일을 찾을 수 없습니다: {project_csv_path}")
        return
        
    df_projects = pd.read_csv(project_csv_path).head(488) # 488개 제약
    
    HEADERS = {
        "accept": "application/json", "content-type": "application/json",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    os.makedirs(save_dir, exist_ok=True)
    final_save_path = os.path.join(save_dir, 'gamefound_final_comments.csv')
    failed_log_path = os.path.join(save_dir, 'failed_projects_log.csv')

    # 기존 데이터 로드 (이어하기)
    completed_ids = set()
    if os.path.exists(final_save_path):
        try:
            existing_df = pd.read_csv(final_save_path)
            if 'project_ID' in existing_df.columns:
                completed_ids = set(existing_df['project_ID'].dropna().astype(int).unique())
                print(f"🔄 [이어하기 활성화] 기존 수집된 {len(completed_ids)}개 프로젝트는 스킵됩니다.\n")
        except Exception as e:
            print(f"⚠️ 기존 파일 읽기 오류 (무시하고 진행): {e}")

    all_comments = []
    failed_projects = [] 
    total_projects = len(df_projects)
    
    try:
        for idx, row in df_projects.iterrows():
            p_name = row.get('name')
            p_id = row.get('projectID')
            p_url = row.get('project_url') # 명확한 URL 사용
            
            if pd.isna(p_name) or pd.isna(p_id) or pd.isna(p_url): 
                continue
            
            p_id_int = int(p_id)
            
            if p_id_int in completed_ids:
                print(f"[{idx+1}/{total_projects}] '{p_name}' ⏭️ 이미 수집됨 (스킵)")
                continue
                
            print(f"[{idx+1}/{total_projects}] '{p_name}' 수집 중...")
            
            thread_id = extract_thread_id_from_url(p_url, HEADERS)
            
            if not thread_id:
                print(f"  ❌ 실패: 댓글이 없거나 URL 오류 (로그 기록됨)")
                failed_projects.append({'projectID': p_id_int, 'name': p_name, 'project_url': p_url})
                continue
                
            comments = fetch_single_project_comments(p_id_int, thread_id, HEADERS)
            all_comments.extend(comments)
            print(f"  ✅ {len(comments)}개 리뷰 신규 확보")
            time.sleep(1.5)
            
    except KeyboardInterrupt: print("\n🚨 강제 중단 감지. 데이터 보존 처리 중...")
    except Exception as e: print(f"\n❌ 에러 발생: {e}")
        
    # 결과 병합 및 저장
    if all_comments:
        df_new = pd.DataFrame(all_comments)
        if os.path.exists(final_save_path):
            df_existing = pd.read_csv(final_save_path)
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            df_combined.to_csv(final_save_path, index=False, encoding="utf-8-sig")
            print(f"\n✅ 기존 데이터에 병합 완료. 총 {len(df_combined):,}건 저장됨: {final_save_path}")
        else:
            df_new.to_csv(final_save_path, index=False, encoding="utf-8-sig")
            print(f"\n✅ 신규 파일 생성 완료. 총 {len(df_new):,}건 저장됨: {final_save_path}")
    else:
        print("\n✅ 이번 실행에서 새롭게 추가된 리뷰가 없습니다.")
        
    # 실패 로그 작성
    if failed_projects:
        pd.DataFrame(failed_projects).to_csv(failed_log_path, index=False, encoding="utf-8-sig")
        print(f"⚠️ {len(failed_projects)}개 프로젝트 수집 불가. 로그 파일 확인: {failed_log_path}")

if __name__ == "__main__":
    # ---------------------------------------------------------
    # [설정] 작업 환경에 맞게 아래 두 경로를 수정하십시오.
    # ---------------------------------------------------------
    
    # 1. 488개의 프로젝트 정보(project_url 포함)가 담긴 원본 CSV 파일의 경로
    PROJECT_LIST_FILE = r"{참조할_프로젝트_리스트_경로.csv}"
    
    # 2. 크롤링된 결과물(csv)을 저장할 대상 폴더 경로
    SAVE_DIRECTORY = r"{결과물을_저장할_폴더_경로}"
    
    run_mass_crawler(PROJECT_LIST_FILE, SAVE_DIRECTORY)